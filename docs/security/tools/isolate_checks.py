"""针对固定上游的无网络函数级证据验证；不启动 Django/FFmpeg/模型。"""
import ast
import json
import os
import sqlite3
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[3]
RESULTS = []
SAVED_MODULES = {key: sys.modules.get(key) for key in ("django", "django.http", "threading")}


def load_defs(relative, names, env):
    """只编译已审阅定义，去除模块导入和装饰器，避免启动上游服务。"""
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8-sig"))
    body = []
    for node in tree.body:
        if getattr(node, "name", None) in names:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                node.decorator_list = []
            body.append(node)
        elif isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id in names for t in node.targets
        ):
            body.append(node)
    module = ast.Module(body=body, type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), relative, "exec"), env)
    return env


class Session(dict):
    """兼容上游 session 接口，仅持有合成身份。"""
    def has_key(self, key):
        return key in self


class Response(dict):
    """捕获响应数据，不访问网络。"""
    def __init__(self, data=b"", status=200, **kwargs):
        super().__init__()
        self.data, self.status_code = data, status


def request(path, method="GET", params=None, user=None):
    """创建没有真实凭据的请求替身。"""
    return types.SimpleNamespace(
        path_info=path, method=method, GET=params or {}, POST=params or {},
        headers={}, META={}, session=Session({"user": user} if user else {}),
    )


def base_env():
    """提供纯本地 helper，日志不写入真实文件。"""
    return {
        "os": os, "HttpResponse": Response,
        "f_parseGetParams": lambda r: r.GET,
        "f_parsePostParams": lambda r: r.POST,
        "LANG_VIEWS_T": lambda *args: args[-1],
        "f_responseJson": lambda d: d, "g_logger": Mock(),
        "f_parseRequestLang": lambda r: "zh",
        "f_parseRequestIp": lambda r: "127.0.0.1",
    }


def record(test_id, observed, detail):
    """同时保存证据验证与产品边界判定，避免将复现成功记为安全通过。"""
    if not observed:
        raise AssertionError(test_id)
    RESULTS.append({"id": test_id, "evidence_check": "PASS",
                    "upstream_security_boundary": "FAIL", "observed": detail})


middleware = load_defs("app/middleware.py", ["AUTH_WHITELIST_PREFIXES", "SimpleMiddleware"],
                       {"MiddlewareMixin": object, "HttpResponseRedirect": lambda p: p})
mw = middleware["SimpleMiddleware"]()
record("F01-ANON-SNAP", mw.process_request(request("/nvr/openSnap")) is None,
       "匿名截图请求被中间件放行；对照 /user/openIndex 返回 /login")
assert mw.process_request(request("/user/openIndex")) == "/login"
record("F02-ANON-INNER", mw.process_request(request("/inner/on_media_delete_stream")) is None,
       "无 Safe、无登录的内部删除回调被放行")

with tempfile.TemporaryDirectory(prefix="rebucca-audit-") as temp:
    env = base_env()
    config = types.SimpleNamespace(storageDir=temp, ffmpeg="ffmpeg",
                                  externalHost="0.0.0.0", mediaRtspPort=10554)
    cls = load_defs("app/utils/ZLMediaKitApi.py", ["ZLMediaKitApi"], {})["ZLMediaKitApi"]
    zlm = cls.__new__(cls)
    zlm._ZLMediaKitApi__config = config
    captured = []
    env.update(g_config=config, g_zlm=zlm,
               subprocess=types.SimpleNamespace(run=lambda cmd, **kw: captured.append((cmd, kw)),
                                                TimeoutExpired=TimeoutError),
               time=types.SimpleNamespace(time=lambda: 1000000, sleep=lambda _: None))
    load_defs("app/views/NvrView.py", ["_capture_snap_file", "_snap_http_response", "api_openSnap"], env)
    taint = "cam_$(printf LOCAL_AUDIT_MARKER)"
    env["api_openSnap"](request("/nvr/openSnap", params={"app": "live", "name": taint, "force": "1"}))
    record("F01-SHELL-DATAFLOW", bool(captured) and taint in captured[0][0]
           and captured[0][1]["shell"] is True,
           "匿名输入未经 URL 编码进入 shell=True 的命令字符串；subprocess 被替身拦截，未执行命令")
    snap_dir = Path(temp) / "snapshots"
    snap_dir.mkdir(exist_ok=True)
    (snap_dir / "live_demo.jpg").write_bytes(b"LOCAL_SAMPLE_" * 12)
    response = env["api_openSnap"](request("/nvr/openSnap", params={"app": "live", "name": "demo"}))
    record("F01-CACHED-IMAGE", response.status_code == 200 and len(response.data) > 100,
           "匿名请求直接读取合成缓存截图；仅访问临时目录样例")

env = base_env()
fake_stream = Mock()
env.update(StreamModel=types.SimpleNamespace(objects=types.SimpleNamespace(
    filter=lambda **kw: types.SimpleNamespace(first=lambda: fake_stream))), g_gb28181SipServer=Mock())
load_defs("app/views/InnerlView.py", ["api_on_media_delete_stream"], env)
response = env["api_on_media_delete_stream"](request("/inner/on_media_delete_stream", "POST", {"code": "toy-camera"}))
record("F02-DELETE-DATAFLOW", response["code"] == 1000 and fake_stream.delete.called,
       "无鉴权请求到达记录删除操作；数据库对象为替身，真实记录未改动")

conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.execute("create table av_stream(code text, camera_device_id text)")
conn.execute("insert into av_stream values('toy-camera','toy-device')")
env = base_env()
env.update(f_checkRequestSafe=lambda r: (True, "ok"),
           g_database=types.SimpleNamespace(select=lambda sql: [dict(r) for r in conn.execute(sql)]),
           g_pull_stream_types=[], get_audio_types=lambda lang: [])
load_defs("app/views/StreamView.py", ["api_openEditContext"], env)
control = env["api_openEditContext"](request("/stream/openEditContext", params={"code": "absent"}))
bad = env["api_openEditContext"](request("/stream/openEditContext", params={"code": "absent' OR 1=1 --"}))
record("F05-SQL", control["code"] == 0 and bad["code"] == 1000,
       "合成 code 改变查询语义，返回本不匹配的摄像头；仅内存 SQLite，无真实凭据")

env = base_env()
env.update(g_session_key_user="user", g_config=types.SimpleNamespace(safe="synthetic-key"))
load_defs("app/views/ViewsBase.py", ["f_sessionReadUser", "f_sessionReadUserId", "f_checkRequestSafe"], env)
user_req = request("/user/openEdit", "POST", {
    "id": "1", "username": "admin", "email": "test@example.invalid", "is_active": "1",
    "new_password": "LocalTest2026", "re_password": "LocalTest2026",
}, {"id": 2, "username": "observer", "is_superuser": 0})
admin = types.SimpleNamespace(username="admin", id=1, set_password=Mock(), save=Mock())
env.update(User=types.SimpleNamespace(objects=types.SimpleNamespace(filter=lambda **kw: types.SimpleNamespace(first=lambda: admin))),
           LogUtils=types.SimpleNamespace(add_user_log=Mock(), LOG_TYPE_EDIT="edit"))
load_defs("app/views/UserView.py", ["api_openEdit"], env)
response = env["api_openEdit"](user_req)
record("F04-ROLE", response["code"] == 1000 and admin.set_password.called,
       "普通合成会话可到达管理员改密码和保存路径；User 为替身，真实用户未改变")

with tempfile.TemporaryDirectory(prefix="rebucca-files-") as temp:
    base = Path(temp) / "storage" / "temp"
    base.mkdir(parents=True)
    (Path(temp) / "private.jpg").write_bytes(b"LOCAL_PRIVATE_SAMPLE")
    class FileResponse(Response):
        """只读取合成样例并立即关闭句柄。"""
        def __init__(self, f, **kw):
            super().__init__(f.read(), **kw)
            f.close()
    fake_http = types.ModuleType("django.http")
    fake_http.FileResponse = FileResponse
    sys.modules["django"] = types.ModuleType("django")
    sys.modules["django.http"] = fake_http
    deletion_calls = []
    class Thread:
        """记录删除计划，但不启动线程或删除任何文件。"""
        def __init__(self, target, args):
            deletion_calls.append(args[0])
        def start(self):
            pass
    sys.modules["threading"] = types.SimpleNamespace(Thread=Thread)
    env = base_env()
    env.update(g_config=types.SimpleNamespace(storageTempDir=str(base)), escape_uri_path=lambda v: v)
    load_defs("app/views/StorageView.py", ["api_openDownload"], env)
    response = env["api_openDownload"](request("/storage/openDownload", params={"filename": "../../private.jpg"}))
    record("F06-FILE-ESCAPE", response.data == b"LOCAL_PRIVATE_SAMPLE" and bool(deletion_calls),
           "下载路径可离开 storageTempDir，且会计划删除该路径；仅临时合成文件，删除线程未执行")

for key, original in SAVED_MODULES.items():
    if original is None:
        sys.modules.pop(key, None)
    else:
        sys.modules[key] = original

summary = {"upstream_commit": "8440b5545fc4f02bad105cbcc1ed09f24a0a2dfd",
           "method": "AST-selected reviewed function bodies, mock requests/services, in-memory SQLite, temporary synthetic files",
           "limits": "No full Django HTTP stack, real shell execution, remote attack, model/binary execution, real credentials or production writes",
           "checks": RESULTS}
(Path(__file__).resolve().parents[1] / "evidence" / "isolated-findings.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"evidence_checks": len(RESULTS), "confirmed_failed_security_boundaries": len(RESULTS),
                  "ids": [r["id"] for r in RESULTS]}, ensure_ascii=False))
