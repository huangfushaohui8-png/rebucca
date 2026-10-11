"""真实Django客户端/ORM验证F01/F02，替身仅用于外部执行/故障注入。"""
import configparser
import json
import os
import stat
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase, override_settings

from app.models import StreamModel
from app.security import prepare_zlm_callback_config, sip_callback_headers, stream_component
from app.snapshot import capture_jpeg, read_jpeg, snapshot_lock
from app.views import InnerlView, NvrView

JPEG = b"\xff\xd8" + b"synthetic-jpeg" * 12 + b"\xff\xd9"


def stream(owner=0, app="live", name="camera1", kind=31, **kwargs):
    """合成真实ORM对象，默认字段来自模型定义，无上游样例数据库。"""
    return StreamModel.objects.create(user_id=owner, sort=0, app=app, name=name, code=name,
                                     pull_stream_type=kind, pull_stream_transfer_mode=0,
                                     pull_stream_port=0, forward_state=0, **kwargs)


def service_headers(service):
    """构建合成测试身份；失败日志从不打印凭据内容。"""
    return {"HTTP_AUTHORIZATION": "Bearer " + os.environ["REBUCCA_%s_CALLBACK_TOKEN" % service.upper()],
            "HTTP_X_REBUCCA_SERVICE": service}


class SnapshotTests(TestCase):
    """F01身份、对象、参数、缓存和失败边界。"""
    def setUp(self):
        """每例独立账户和流；捕获替身只产生标记JPEG，不访问摄像头。"""
        directory = tempfile.TemporaryDirectory(prefix="snapshot-test-")
        self.addCleanup(directory.cleanup)
        override = override_settings(REBUCCA_SNAPSHOT_DIR=directory.name)
        override.enable()
        self.addCleanup(override.disable)
        self.owner = User.objects.create(username="owner")
        self.other = User.objects.create(username="other")
        self.admin = User.objects.create(username="admin", is_superuser=True)
        self.camera = stream(self.owner.id)
        self.capture = patch("app.views.NvrView._capture_snap_file", return_value=JPEG).start()
        self.addCleanup(patch.stopall)

    def login(self, user, **extra):
        """沿用产品自有session.user契约，不使用Django登录来掩盖兼容性。"""
        session = self.client.session
        session["user"] = dict(id=user.id, **extra)
        session.save()

    def get(self, **params):
        """直接请求现有app/name截图接口。"""
        return self.client.get("/nvr/openSnap", dict(app="live", name="camera1", **params))

    def test_anonymous_denied_before_capture(self):
        """匿名不能到达缓存或媒体执行。"""
        self.assertEqual(self.get().status_code, 401)
        self.capture.assert_not_called()

    def test_legacy_safe_does_not_authorize(self):
        """旧Safe不升级为浏览器/对象访问授权。"""
        response = self.client.get("/nvr/openSnap?app=live&name=camera1", HTTP_SAFE="legacy-test-safe")
        self.assertEqual(response.status_code, 401)

    def test_owner_can_snapshot(self):
        """所有者正常截图有正确MIME和缓存策略。"""
        self.login(self.owner)
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, JPEG)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(self.capture.call_args.args[0], "rtsp://127.0.0.1:10554/live/camera1")

    def test_other_owner_denied(self):
        """跨流读取没有执行副作用。"""
        self.login(self.other)
        self.assertEqual(self.get().status_code, 403)
        self.capture.assert_not_called()

    def test_admin_can_read_registered_stream(self):
        """当前数据库管理员可读其他所有者登记流。"""
        self.login(self.admin)
        self.assertEqual(self.get().status_code, 200)

    def test_session_admin_flag_not_trusted(self):
        """伪造/过期会话角色不能代替数据库当前角色。"""
        self.login(self.other, is_superuser=True)
        self.assertEqual(self.get().status_code, 403)

    def test_role_revocation_applies_immediately(self):
        """管理员撤权后即使会话仍有旧标记也被拒。"""
        self.login(self.admin, is_superuser=True)
        User.objects.filter(id=self.admin.id).update(is_superuser=False)
        self.assertEqual(self.get().status_code, 403)

    def test_disabled_and_deleted_users_denied(self):
        """停用和删除用户都不能从旧session读取截图。"""
        self.login(self.owner)
        User.objects.filter(id=self.owner.id).update(is_active=False)
        self.assertEqual(self.get().status_code, 401)
        self.owner.delete()
        self.assertEqual(self.get().status_code, 401)

    def test_system_created_stream_requires_admin(self):
        """user_id=0不会被普通用户当作公有资源。"""
        StreamModel.objects.filter(id=self.camera.id).update(user_id=0)
        self.login(self.owner)
        self.assertEqual(self.get().status_code, 403)
        self.login(self.admin)
        self.assertEqual(self.get().status_code, 200)

    def test_bad_session_id_denied(self):
        """异常身份结构失败关闭。"""
        for value in (True, -1, "1", [], None):
            session = self.client.session
            session["user"] = {"id": value}
            session.save()
            self.assertEqual(self.get().status_code, 401)

    def test_invalid_identifiers_denied(self):
        """独立恶意输入集覆盖shell、路径、URL、Unicode和长度。"""
        self.login(self.owner)
        for value in ("", ".", "..", "../cam", "a/b", "a\\b", "a\x00b", "cam\n", "cam ",
                      'cam"', "$(id)", "`id`", "a;b", "a?b", "a#b", "a%2fb", "摄像头", "a" * 51):
            with self.subTest(kind="invalid_identifier"):
                self.assertEqual(self.client.get("/nvr/openSnap", {"app": "live", "name": value}).status_code, 400)
        self.capture.assert_not_called()

    def test_duplicate_query_and_bad_force_denied(self):
        """拒绝歧义查询和异常强制刷新参数。"""
        self.login(self.owner)
        for query in ("app=live&app=live&name=camera1", "app=live&name=camera1&name=other",
                      "app=live&name=camera1&force=1&force=0", "app=live&name=camera1&force=true"):
            self.assertEqual(self.client.get("/nvr/openSnap?" + query).status_code, 400)

    def test_method_and_unknown_object(self):
        """只允许GET和登记对象。"""
        self.login(self.owner)
        self.assertEqual(self.client.post("/nvr/openSnap").status_code, 405)
        self.assertEqual(self.client.get("/nvr/openSnap?app=live&name=missing").status_code, 404)

    def test_ambiguous_stream_denied(self):
        """无唯一约束的旧数据库不允许静默选错所有者。"""
        stream(self.other.id)
        self.login(self.owner)
        self.assertEqual(self.get().status_code, 409)

    def test_private_cache_still_checks_owner(self):
        """缓存不能绕过身份或对象授权。"""
        directory = Path(settings.REBUCCA_SNAPSHOT_DIR)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / ("stream-%d.jpg" % self.camera.id)).write_bytes(JPEG)
        self.assertEqual(self.get().status_code, 401)
        self.login(self.other)
        self.assertEqual(self.get().status_code, 403)
        self.login(self.owner)
        self.assertEqual(self.get().content, JPEG)
        self.capture.assert_not_called()

    def test_force_bypasses_cache(self):
        """授权force刷新依然执行安全路径。"""
        self.login(self.owner)
        self.assertEqual(self.get(force="1").status_code, 200)
        self.capture.assert_called_once()

    def test_public_cache_configuration_rejected(self):
        """误配置不能把新的受保护截图放回static。"""
        self.login(self.owner)
        with override_settings(REBUCCA_SNAPSHOT_DIR=str(settings.BASE_DIR / "static" / "snapshots")):
            self.assertEqual(self.get().status_code, 400)
        self.capture.assert_not_called()

    def test_external_url_parameters_ignored(self):
        """用户传入URL/请求IP不会改变本机媒体目的地。"""
        self.login(self.owner)
        self.assertEqual(self.get(request_ip="198.51.100.8", rtsp_url="file:///etc/passwd").status_code, 200)
        self.assertEqual(self.capture.call_args.args[0], "rtsp://127.0.0.1:10554/live/camera1")

    def test_timeout_has_no_sensitive_error(self):
        """超时不返回原命令/秘密/旧缓存。"""
        self.login(self.owner)
        self.capture.side_effect = subprocess.TimeoutExpired("private-command", 12)
        response = self.get(force="1")
        self.assertEqual(response.status_code, 504)
        self.assertNotIn(b"private-command", response.content)

    def test_capture_failure_bounded_retry(self):
        """非零/无帧失败只重试一次并明确失败。"""
        self.login(self.owner)
        self.capture.return_value = None
        with patch("app.views.NvrView.time.sleep"):
            self.assertEqual(self.get(force="1").status_code, 502)
        self.assertEqual(self.capture.call_count, 2)

    def test_concurrent_capture_denied(self):
        """同流并发锁使额外刷新不生成额外媒体进程。"""
        self.login(self.owner)
        with patch("app.views.NvrView.snapshot_lock") as lock:
            lock.return_value.__enter__.return_value = False
            self.assertEqual(self.get(force="1").status_code, 429)
        self.capture.assert_not_called()


class CallbackTests(TestCase):
    """F02真实路由/HTTP/ORM的身份、协议对象边界和正常路径。"""
    def setUp(self):
        """每例独立视频库和SIP副作用记录。"""
        InnerlView.g_gb28181SipServer.reset_mock()
        self.params = dict(app="rtp", name="34020000001320000001", ip="192.0.2.10", port=5060,
                           clientId="34020000002000000001", pullStreamType=21,
                           pullStreamUrl="rtp://__", cameraName="合成摄像头", forwardState=1)
        self.zlm = dict(app="live", stream="camera1", schema="rtsp", ip="192.0.2.20", port=30000, id="client1")

    def post(self, route, payload=None, service=None, **headers):
        """真实客户端，经真实中间件与视图进入真实ORM。"""
        if service:
            headers = dict(service_headers(service), **headers)
        return self.client.post("/inner/" + route, json.dumps(payload if payload is not None else self.params),
                                content_type="application/json", **headers)

    def test_anonymous_all_four_callbacks_denied(self):
        """四个回调匿名访问均在写入/删除/邀请前拒绝。"""
        for route in ("on_media_update_stream", "on_media_delete_stream", "on_publish", "on_stream_not_found"):
            self.assertEqual(self.post(route).status_code, 401)
        self.assertEqual(StreamModel.objects.count(), 0)
        InnerlView.g_gb28181SipServer.request_invite.assert_not_called()

    def test_session_and_legacy_safe_do_not_authorize(self):
        """网页管理员身份和旧Safe不是内部服务身份。"""
        session = self.client.session
        session["user"] = {"id": 1, "is_superuser": True}
        session.save()
        self.assertEqual(self.post("on_media_update_stream", HTTP_SAFE="legacy-test-safe").status_code, 401)

    def test_wrong_token_and_cross_service_denied(self):
        """猜测token、跨身份token和伪装服务名不能授权。"""
        response = self.post("on_media_update_stream", HTTP_AUTHORIZATION="Bearer " + "0" * 64,
                             HTTP_X_REBUCCA_SERVICE="sip")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.post("on_media_update_stream", service="zlm").status_code, 401)
        self.assertEqual(self.post("on_publish", self.zlm, "sip").status_code, 401)

    def test_missing_and_shared_secrets_fail_closed(self):
        """缺失、无效长度和两服务共用secret一律不能退回旧Safe。"""
        for value in ("", "default", os.environ["REBUCCA_ZLM_CALLBACK_TOKEN"]):
            with patch.dict(os.environ, REBUCCA_SIP_CALLBACK_TOKEN=value):
                self.assertEqual(self.post("on_media_update_stream", service="sip").status_code, 503)

    def test_non_loopback_denied_even_with_token(self):
        """token泄露也不能从外部对端直接调用本轮入口。"""
        for ip in ("192.0.2.1", "10.0.0.4", "", "not-ip"):
            self.assertEqual(self.post("on_media_update_stream", service="sip", REMOTE_ADDR=ip).status_code, 403)

    def test_forwarded_header_not_trusted(self):
        """代理来源声明不扩大回环许可。"""
        for name in ("HTTP_X_FORWARDED_FOR", "HTTP_FORWARDED", "HTTP_X_REAL_IP"):
            self.assertEqual(self.post("on_media_update_stream", service="sip", **{name: "127.0.0.1"}).status_code, 403)

    def test_ipv6_loopback_supported(self):
        """真正IPv6回环保留兼容性。"""
        self.assertEqual(self.post("on_media_update_stream", service="sip", REMOTE_ADDR="::1").status_code, 200)

    def test_unknown_route_and_method_denied(self):
        """不能靠inner前缀或接口前缀混淆获得放行。"""
        self.assertEqual(self.post("unknown", service="sip").status_code, 404)
        self.assertEqual(self.post("on_media_update_stream_extra", service="sip").status_code, 404)
        self.assertEqual(self.client.get("/inner/on_media_update_stream", **service_headers("sip")).status_code, 405)

    def test_view_auth_without_middleware(self):
        """直接调用视图仍然拒绝匿名，避免中间件遗漏。"""
        request = RequestFactory().post("/inner/on_media_update_stream", data=json.dumps(self.params),
                                        content_type="application/json")
        self.assertEqual(InnerlView.api_on_media_update_stream(request).status_code, 401)

    def test_json_type_size_content_type_and_syntax(self):
        """回调解析边界在数据库变化之前执行。"""
        for raw in ("{", "[]", '"string"', "null", '{"app":"rtp","app":"live"}'):
            self.assertEqual(self.client.post("/inner/on_media_update_stream", raw,
                                             content_type="application/json", **service_headers("sip")).status_code, 400)
        self.assertEqual(self.client.post("/inner/on_media_update_stream", self.params,
                                         **service_headers("sip")).status_code, 415)
        self.assertEqual(self.client.post("/inner/on_media_update_stream", " " * 65537,
                                         content_type="application/json", **service_headers("sip")).status_code, 413)
        self.assertEqual(StreamModel.objects.count(), 0)

    def test_ambiguous_stream_code_cannot_delete_or_update(self):
        """重复编号旧记录不能被服务回调静默选中并破坏。"""
        stream(app="rtp", name=self.params["name"], kind=21)
        stream(app="rtp", name=self.params["name"], kind=21)
        update = self.post("on_media_update_stream", service="sip")
        self.assertEqual(update.json()["code"], 0)
        deletion = self.post("on_media_delete_stream", {"code": self.params["name"]}, "sip")
        self.assertEqual(deletion.json()["code"], 0)
        self.assertEqual(StreamModel.objects.count(), 2)
        InnerlView.g_gb28181SipServer.remove_channel.assert_not_called()

    def test_invalid_update_fields_have_no_side_effect(self):
        """异常参数不进入SQL、对象创建或设备控制。"""
        mutations = [("name", "../camera"), ("app", "live"), ("pullStreamType", 1), ("ip", "x;id"),
                     ("port", 65536), ("port", 1.2), ("forwardState", True), ("forwardState", 2),
                     ("clientId", []), ("cameraName", None), ("lastKeepaliveTime", 2**63),
                     ("pullStreamUrl", "rtsp://evil")]
        for key, value in mutations:
            self.assertEqual(self.post("on_media_update_stream", dict(self.params, **{key: value}), "sip").status_code, 400)
        self.assertEqual(StreamModel.objects.count(), 0)

    def test_valid_update_create_and_repeat_preserve_owner(self):
        """正常GB28181同步有真实库回执，重复同步不改变拥有者。"""
        response = self.post("on_media_update_stream", service="sip")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 1000)
        item = StreamModel.objects.get(code=self.params["name"])
        self.assertEqual(item.user_id, 0)
        self.assertEqual(item.pull_stream_type, 21)
        item.user_id = 7
        item.save()
        self.assertEqual(self.post("on_media_update_stream", service="sip").json()["code"], 1000)
        item.refresh_from_db()
        self.assertEqual(item.user_id, 7)
        self.assertEqual(StreamModel.objects.count(), 1)

    def test_sip_cannot_modify_or_delete_manual_stream(self):
        """服务身份也不能越过协议/对象范围改写手工拉流。"""
        item = stream(7, app="live", name=self.params["name"], kind=1)
        self.assertEqual(self.post("on_media_update_stream", service="sip").status_code, 403)
        self.assertEqual(self.post("on_media_delete_stream", {"code": item.code}, "sip").status_code, 403)
        item.refresh_from_db()
        self.assertEqual(item.app, "live")
        self.assertEqual(item.user_id, 7)
        InnerlView.g_gb28181SipServer.remove_channel.assert_not_called()

    def test_valid_sip_delete(self):
        """合法删除仅影响匹配的GB28181流。"""
        item = stream(app="rtp", name=self.params["name"], kind=21)
        self.assertEqual(self.post("on_media_delete_stream", {"code": item.code}, "sip").json()["code"], 1000)
        self.assertFalse(StreamModel.objects.filter(id=item.id).exists())
        InnerlView.g_gb28181SipServer.remove_channel.assert_called_once_with(item.code)

    def test_zlm_native_query_token_and_header_supported(self):
        """原生hook查询token和专用身份头都可进行正常发布。"""
        token = os.environ["REBUCCA_ZLM_CALLBACK_TOKEN"]
        response = self.client.post("/inner/on_publish?callback_token=" + token, json.dumps(self.zlm),
                                    content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 0)
        self.assertEqual(self.post("on_publish", self.zlm, "zlm").json()["code"], 0)
        self.assertEqual(StreamModel.objects.count(), 1)

    def test_query_token_not_allowed_for_sip_or_ambiguous(self):
        """SIP仅身份头；重复/混合token不能引入身份歧义。"""
        token = os.environ["REBUCCA_ZLM_CALLBACK_TOKEN"]
        for query in ("callback_token=" + token + "&callback_token=" + token,):
            self.assertEqual(self.client.post("/inner/on_publish?" + query, json.dumps(self.zlm),
                                             content_type="application/json").status_code, 401)
        self.assertEqual(self.client.post("/inner/on_publish?callback_token=" + token, json.dumps(self.zlm),
                                         content_type="application/json", **service_headers("zlm")).status_code, 401)
        sip_token = os.environ["REBUCCA_SIP_CALLBACK_TOKEN"]
        self.assertEqual(self.client.post("/inner/on_media_update_stream?callback_token=" + sip_token,
                                         json.dumps(self.params), content_type="application/json").status_code, 401)

    def test_zlm_cannot_overwrite_different_protocol(self):
        """发布不能覆盖手工拉流或跨app同code记录。"""
        item = stream(owner=8, kind=1)
        response = self.post("on_publish", self.zlm, "zlm")
        self.assertEqual(response.json()["code"], -1)
        item.refresh_from_db()
        self.assertEqual(item.pull_stream_type, 1)
        self.assertEqual(item.user_id, 8)

    def test_not_found_invites_only_matching_gb_stream(self):
        """按需邀请的参数来自登记对象；其他协议同code不触发设备动作。"""
        item = stream(app="rtp", name=self.params["name"], kind=21, camera_device_id="device1")
        response = self.post("on_stream_not_found", {"app": "rtp", "stream": item.name}, "zlm")
        self.assertEqual(response.json()["code"], 0)
        InnerlView.g_gb28181SipServer.request_invite.assert_called_once_with(client_id="device1", channel_id=item.name)
        InnerlView.g_gb28181SipServer.reset_mock()
        item.pull_stream_type = 1
        item.save()
        self.post("on_stream_not_found", {"app": "rtp", "stream": item.name}, "zlm")
        InnerlView.g_gb28181SipServer.request_invite.assert_not_called()

    def test_public_routes_and_existing_session_route(self):
        """中间件收紧不会禁止已有登录入口与登录后的业务路由。"""
        self.assertEqual(self.client.get("/login").status_code, 200)
        self.assertEqual(self.client.get("/user/openCaptcha").status_code, 200)
        self.assertEqual(self.client.get("/stream/index").status_code, 302)
        session = self.client.session
        session["user"] = {"id": 1}
        session.save()
        self.assertEqual(self.client.get("/stream/index").status_code, 200)


class ExecutorAndSenderTests(TestCase):
    """进程调用契约、私有配置与真实SIP发送方法的隔离验证。"""
    def test_capture_uses_argv_without_shell_and_atomic_cache(self):
        """检查实际进程入口传参并注入JPEG产物，验证发布/清理行为。"""
        with tempfile.TemporaryDirectory() as directory:
            exe = Path(directory) / "ffmpeg"
            exe.write_text("synthetic executable")
            exe.chmod(0o700)
            destination = Path(directory) / "camera.jpg"
            def synthetic_run(argv, **kwargs):
                """独立预期：URL是单个参数，永不由shell解释。"""
                self.assertIsInstance(argv, list)
                self.assertFalse(kwargs["shell"])
                self.assertEqual(kwargs["timeout"], 12)
                self.assertEqual(argv[argv.index("-i") + 1], "rtsp://127.0.0.1:10554/live/camera1")
                Path(argv[-1]).write_bytes(JPEG)
                return SimpleNamespace(returncode=0)
            with patch("app.snapshot.subprocess.run", side_effect=synthetic_run):
                self.assertEqual(capture_jpeg("rtsp://127.0.0.1:10554/live/camera1", destination, str(exe)), JPEG)
            self.assertEqual(destination.read_bytes(), JPEG)
            self.assertEqual(len(list(Path(directory).glob("snap-*"))), 0)

    def test_failure_and_timeout_keep_old_cache_and_clean_temp(self):
        """失败不能返回/覆盖旧缓存，超时之后临时文件也清理。"""
        with tempfile.TemporaryDirectory() as directory:
            exe = Path(directory) / "ffmpeg"
            exe.write_text("synthetic executable")
            exe.chmod(0o700)
            destination = Path(directory) / "camera.jpg"
            destination.write_bytes(JPEG)
            with patch("app.snapshot.subprocess.run", return_value=SimpleNamespace(returncode=1)):
                self.assertIsNone(capture_jpeg("rtsp://127.0.0.1:10554/live/camera1", destination, str(exe)))
            with patch("app.snapshot.subprocess.run", side_effect=subprocess.TimeoutExpired("private", 12)):
                with self.assertRaises(subprocess.TimeoutExpired):
                    capture_jpeg("rtsp://127.0.0.1:10554/live/camera1", destination, str(exe))
            self.assertEqual(destination.read_bytes(), JPEG)
            self.assertFalse(list(Path(directory).glob("snap-*")))

    def test_untrusted_executable_rejected(self):
        """命令字符串、相对可执行和脚本包装器不作为可信FFmpeg。"""
        with patch("app.snapshot.subprocess.run") as process:
            for exe in ("ffmpeg", "ffmpeg; id", "/missing/ffmpeg", "./ffmpeg"):
                with self.assertRaises(ValueError):
                    capture_jpeg("rtsp://127.0.0.1/live/cam", "/tmp/unused.jpg", exe)
            process.assert_not_called()

    def test_symlink_and_invalid_jpeg_not_read(self):
        """缓存读取拒绝软链接与非JPEG字节。"""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "file"
            target.write_bytes(b"x" * 150)
            self.assertIsNone(read_jpeg(target))
            link = Path(directory) / "link"
            link.symlink_to(target)
            if hasattr(os, "O_NOFOLLOW"):
                with self.assertRaises(OSError):
                    read_jpeg(link)

    def test_real_filesystem_lock_excludes_competing_open(self):
        """实际OS锁覆盖独立文件描述符，释放后可再获得。"""
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "stream.lock"
            with snapshot_lock(lock) as first:
                self.assertTrue(first)
                with snapshot_lock(lock) as second:
                    self.assertFalse(second)
            with snapshot_lock(lock) as third:
                self.assertTrue(third)

    def test_zlm_config_has_private_per_service_hooks(self):
        """真实INI模板复制，注入只在0600运行文件中，原文件保持原字节。"""
        source = settings.BASE_DIR / "zlm/bin.x86.gcc9.4/config.ini"
        original = source.read_bytes()
        generated = Path(prepare_zlm_callback_config(source, 10001))
        self.addCleanup(generated.unlink, missing_ok=True)
        config = configparser.ConfigParser(interpolation=None)
        config.read(generated)
        self.assertEqual(stat.S_IMODE(generated.stat().st_mode), 0o600)
        for route in ("on_publish", "on_stream_not_found"):
            url = urlsplit(config.get("hook", route))
            self.assertEqual(url.hostname, "127.0.0.1")
            self.assertEqual(url.path, "/inner/" + route)
            self.assertTrue(parse_qs(url.query)["callback_token"][0] == os.environ["REBUCCA_ZLM_CALLBACK_TOKEN"])
        self.assertEqual(source.read_bytes(), original)
        self.assertIn("timeoutSec", generated.read_text())
        self.assertNotIn("static", generated.relative_to(Path(settings.REBUCCA_PRIVATE_RUNTIME_DIR).parent).parts)

    def test_zlm_cannot_start_without_callback_credentials(self):
        """启动入口失败关闭，不只验证配置辅助函数。"""
        from app.utils.MediaServerManager import MediaServerManager
        manager = MediaServerManager()
        config = settings.BASE_DIR / "zlm/bin.x86.gcc9.4/config.ini"
        with patch.dict(os.environ, REBUCCA_ZLM_CALLBACK_TOKEN=""), patch.object(manager, "api_alive", return_value=False), \
                patch.object(manager, "_paths", return_value=(__file__, str(config))), patch("subprocess.Popen") as process:
            ok, _msg = manager.start()
            self.assertFalse(ok)
            process.assert_not_called()

    def test_sip_destination_boundary(self):
        """SIP凭据不发送到非回环、其他路径或不安全URL。"""
        for url in ("http://192.0.2.1/inner/on_media_update_stream", "http://localhost/inner/on_media_update_stream",
                    "http://127.0.0.1/other", "https://127.0.0.1/inner/on_media_update_stream",
                    "http://user:pass@127.0.0.1/inner/on_media_update_stream"):
            with self.assertRaises(ValueError):
                sip_callback_headers(url)

    def test_real_sip_sender_adds_identity_and_disables_redirect(self):
        """执行真实Channel.update_admin，外部HTTP传输是唯一替身。"""
        from app.utils.GB28181SipServer import Channel, Device
        device = Device("34020000002000000001", ip="192.0.2.10", port=5060)
        channel = Channel("34020000001320000001", device=device, logger=Mock())
        server = SimpleNamespace(admin_host="http://127.0.0.1:10001", lock=threading.Lock(),
                                 devices={device.device_id: device}, rtp_transfer_mode=0, rtp_transfer_audio_type=0)
        with patch("app.utils.GB28181SipServer.requests.post") as post:
            post.return_value.status_code = 200
            post.return_value.json.return_value = {"code": 1000}
            self.assertTrue(channel.update_admin(server)[0])
            kwargs = post.call_args.kwargs
            self.assertEqual(kwargs["headers"]["X-Rebucca-Service"], "sip")
            self.assertTrue(kwargs["headers"]["Authorization"].startswith("Bearer "))
            self.assertFalse(kwargs["allow_redirects"])
            self.assertEqual(kwargs["json"]["name"], channel.channel_id)


class SyntheticVideoTests(TestCase):
    """网络被隔离的容器内，用回环合成RTSP验证真实FFmpeg与真实截图视图。"""
    @skipUnless(os.environ.get("REBUCCA_TEST_RTSP") == "1", "synthetic RTSP requires network-none container")
    def test_real_ffmpeg_synthetic_rtsp_snapshot(self):
        """只在容器回环启动短时合成RTSP fixture，不连接摄像头。"""
        from tests.synthetic_rtsp import SyntheticRTSP
        user = User.objects.create(username="synthetic-video-owner")
        item = stream(owner=user.id, name="synthetic-video")
        session = self.client.session
        session["user"] = {"id": user.id}
        session.save()
        with SyntheticRTSP():
            response = self.client.get("/nvr/openSnap", {"app": item.app, "name": item.name, "force": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"\xff\xd8"))
        self.assertTrue(response.content.endswith(b"\xff\xd9"))
        self.assertGreater(len(response.content), 100)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(response["Cache-Control"], "no-store")
