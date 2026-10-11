# 官网：https://www.yuturuishi.com
# 微信：yuturuishi
# gitee开源地址：https://gitee.com/yuturuishi/rebucca
# github开源地址：https://github.com/yuturuishi/rebucca
"""
NvrView 模块 — 24/7 录像 + FFmpeg 截图
"""
import os
import time
import subprocess
from datetime import timedelta
from app.views.ViewsBase import *
from app.utils.Utils import buildPageLabels
from app.utils.LanguageUtils import LANG_VIEWS_T
from django.http import HttpResponse
from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.models import User
from app.security import stream_component, private_directory
from app.snapshot import capture_jpeg, local_rtsp_url, read_jpeg, snapshot_lock


def record_index(request):
    params = f_parseGetParams(request)
    stream_id = int(params.get("stream_id", 0) or 0)
    stream_name = ""
    record_enable = 0
    is_recording = False
    if stream_id:
        from app.models import StreamModel
        stream = StreamModel.objects.filter(id=stream_id).first()
        if stream:
            stream_name = stream.nickname or stream.name or ("#" + str(stream_id))
            record_enable = int(stream.record_enable or 0)
            try:
                from app.recording.manager import get_recording_manager
                is_recording = get_recording_manager().is_recording(stream_id)
            except Exception:
                pass
        else:
            stream_id = 0
    if not stream_id:
        from django.shortcuts import redirect
        return redirect("/stream/index")
    return render(request, "app/record/index.html", {
        "stream_id": stream_id,
        "stream_name": stream_name,
        "record_enable": record_enable,
        "is_recording": is_recording,
    })


def _sync_stream_recording(stream):
    """根据 record_enable 与转发状态同步录像进程（关闭录像时停止进程，保留历史文件）"""
    try:
        from app.recording.manager import get_recording_manager
        mgr = get_recording_manager()
        if int(stream.record_enable or 0) == 1 and int(stream.forward_state or 0) == 1:
            mgr.start_stream(stream)
        else:
            mgr.stop_stream(stream.id)
    except Exception as e:
        g_logger.warning("sync recording stream=%s err: %s" % (stream.id, str(e)))


def _get_stream(params):
    from app.models import StreamModel
    sid = int(params.get("stream_id") or params.get("id") or 0)
    app = (params.get("app") or "").strip()
    name = (params.get("name") or "").strip()
    if sid:
        return StreamModel.objects.filter(id=sid).first()
    if app and name:
        return StreamModel.objects.filter(app=app, name=name).first()
    return None


def api_openVideoIsRecording(request):
    if request.method != 'GET':
        return f_responseJson({"code": 0, "msg": LANG_VIEWS_T(request, "msg_method_not_supported")})
    __check_ret, __check_msg = f_checkRequestSafe(request)
    if not __check_ret:
        return f_responseJson({"code": 0, "msg": __check_msg})
    params = f_parseGetParams(request)
    stream = _get_stream(params)
    if not stream:
        return f_responseJson({"code": 0, "msg": "stream not found"})
    from app.recording.manager import get_recording_manager
    mgr = get_recording_manager()
    return f_responseJson({
        "code": 1000, "msg": "ok",
        "is_recording": mgr.is_recording(stream.id),
        "record_enable": stream.record_enable,
    })


def api_openStartRecordVideo(request):
    if request.method != 'POST':
        return f_responseJson({"code": 0, "msg": LANG_VIEWS_T(request, "msg_method_not_supported")})
    __check_ret, __check_msg = f_checkRequestSafe(request)
    if not __check_ret:
        return f_responseJson({"code": 0, "msg": __check_msg})
    params = f_parsePostParams(request)
    stream = _get_stream(params)
    if not stream:
        return f_responseJson({"code": 0, "msg": "stream not found"})
    stream.record_enable = 1
    stream.save(update_fields=["record_enable"])
    from app.recording.manager import get_recording_manager
    ok, info = get_recording_manager().start_stream(stream)
    return f_responseJson({"code": 1000 if ok else 0, "msg": info})


def api_openStopRecordVideo(request):
    if request.method != 'POST':
        return f_responseJson({"code": 0, "msg": LANG_VIEWS_T(request, "msg_method_not_supported")})
    __check_ret, __check_msg = f_checkRequestSafe(request)
    if not __check_ret:
        return f_responseJson({"code": 0, "msg": __check_msg})
    params = f_parsePostParams(request)
    stream = _get_stream(params)
    if not stream:
        return f_responseJson({"code": 0, "msg": "stream not found"})
    stream.record_enable = 0
    stream.save(update_fields=["record_enable"])
    from app.recording.manager import get_recording_manager
    ok, info = get_recording_manager().stop_stream(stream.id)
    return f_responseJson({"code": 1000 if ok else 0, "msg": info})


def _scan_disk_recordings(stream_id=None):
    """从磁盘扫描录像分段（FFmpeg segment 输出）"""
    items = []
    try:
        base = g_config.storageRecordDir
    except Exception:
        return items
    if not base or not os.path.isdir(base):
        return items
    for root, _dirs, files in os.walk(base):
        for fn in files:
            if not fn.lower().endswith((".mp4", ".ts", ".mkv")):
                continue
            fp = os.path.join(root, fn)
            try:
                st = os.stat(fp)
            except Exception:
                continue
            sid = 0
            parts = fn.split("_", 1)
            if parts and parts[0].isdigit():
                sid = int(parts[0])
            if stream_id and sid != int(stream_id):
                continue
            from datetime import datetime
            start = datetime.fromtimestamp(st.st_mtime)
            items.append({
                "id": 0,
                "stream_id": sid,
                "stream_name": "",
                "file_path": fp,
                "start_time": str(start),
                "end_time": str(start),
                "duration": 0,
                "file_size": st.st_size,
                "file_exists": True,
            })
    items.sort(key=lambda x: x["start_time"], reverse=True)
    return items


def api_openRecordIndex(request):
    """分页列出录像分段"""
    if request.method != 'GET':
        return f_responseJson({"code": 0, "msg": LANG_VIEWS_T(request, "msg_method_not_supported")})
    __check_ret, __check_msg = f_checkRequestSafe(request)
    if not __check_ret:
        return f_responseJson({"code": 0, "msg": __check_msg})
    from app.models import RecordingModel, StreamModel
    params = f_parseGetParams(request)
    page = int(params.get('p', 1) or 1)
    ps = int(params.get('ps', 20) or 20)
    sid = params.get('stream_id')
    stream_filter = int(sid) if sid else None

    qs = RecordingModel.objects.all().order_by('-start_time')
    if stream_filter:
        qs = qs.filter(stream_id=stream_filter)
    db_rows = list(qs.select_related('stream')[:500])
    data = []
    seen_paths = set()
    for r in db_rows:
        seen_paths.add(r.file_path)
        data.append({
            "id": r.id,
            "stream_id": r.stream_id,
            "stream_name": (r.stream.nickname if r.stream else ""),
            "file_path": r.file_path,
            "start_time": str(r.start_time),
            "end_time": str(r.end_time),
            "duration": r.duration,
            "file_size": r.file_size,
            "file_exists": os.path.isfile(r.file_path) if r.file_path else False,
        })
    for item in _scan_disk_recordings(stream_filter):
        if item["file_path"] in seen_paths:
            continue
        if item["stream_id"]:
            try:
                s = StreamModel.objects.filter(id=item["stream_id"]).first()
                if s:
                    item["stream_name"] = s.nickname or s.name
            except Exception:
                pass
        data.append(item)
    data.sort(key=lambda x: x.get("start_time", ""), reverse=True)
    count = len(data)
    skip = (page - 1) * ps
    page_rows = data[skip:skip + ps]
    page_num = int(count / ps) + (1 if count % ps else 0)
    page_data = {
        "page": page, "page_size": ps, "page_num": max(1, page_num), "count": count,
        "pageLabels": buildPageLabels(page=page, page_num=max(1, page_num), lang=f_parseRequestLang(request)),
    }
    return f_responseJson({"code": 1000, "msg": "ok", "data": page_rows, "pageData": page_data})


def api_openRecordFile(request):
    if request.method != 'GET':
        return HttpResponse(b"method not allowed", status=405)
    __check_ret, __check_msg = f_checkRequestSafe(request)
    if not __check_ret:
        return HttpResponse(__check_msg.encode("utf-8"), status=403)
    params = f_parseGetParams(request)
    rid = int(params.get("id", 0) or 0)
    fpath = (params.get("path") or "").strip()
    fp = None
    if rid:
        from app.models import RecordingModel
        try:
            rec = RecordingModel.objects.get(id=rid)
            fp = rec.file_path
        except Exception:
            return HttpResponse(b"not found", status=404)
    elif fpath and os.path.isfile(fpath):
        try:
            base = g_config.storageRecordDir
            if base and os.path.commonpath([os.path.abspath(fpath), os.path.abspath(base)]) == os.path.abspath(base):
                fp = fpath
        except Exception:
            pass
    if not fp or not os.path.isfile(fp):
        return HttpResponse(b"file missing", status=404)
    with open(fp, "rb") as f:
        data = f.read()
    resp = HttpResponse(data, content_type="video/mp4")
    resp["Content-Disposition"] = 'inline; filename="%s"' % os.path.basename(fp)
    return resp


def api_openRecordDel(request):
    if request.method != 'POST':
        return f_responseJson({"code": 0, "msg": LANG_VIEWS_T(request, "msg_method_not_supported")})
    __check_ret, __check_msg = f_checkRequestSafe(request)
    if not __check_ret:
        return f_responseJson({"code": 0, "msg": __check_msg})
    params = f_parsePostParams(request)
    rid = int(params.get("id", 0) or 0)
    fpath = (params.get("path") or "").strip()
    if not rid and not fpath:
        return f_responseJson({"code": 0, "msg": "missing id or path"})
    from app.models import RecordingModel
    try:
        if rid:
            rec = RecordingModel.objects.get(id=rid)
            fp = rec.file_path
            rec.delete()
        else:
            fp = fpath
            base = g_config.storageRecordDir
            if not base or not os.path.isfile(fp):
                return f_responseJson({"code": 0, "msg": "file missing"})
            if os.path.commonpath([os.path.abspath(fp), os.path.abspath(base)]) != os.path.abspath(base):
                return f_responseJson({"code": 0, "msg": "invalid path"})
            RecordingModel.objects.filter(file_path=fp).delete()
        if fp and os.path.isfile(fp):
            os.remove(fp)
        return f_responseJson({"code": 1000, "msg": LANG_VIEWS_T(request, "msg_success")})
    except Exception as e:
        return f_responseJson({"code": 0, "msg": str(e)})


def api_openSnapShot(request):
    if request.method != 'POST':
        return f_responseJson({"code": 0, "msg": LANG_VIEWS_T(request, "msg_method_not_supported")})
    __check_ret, __check_msg = f_checkRequestSafe(request)
    if not __check_ret:
        return f_responseJson({"code": 0, "msg": __check_msg})
    return f_responseJson({"code": 0, "msg": LANG_VIEWS_T(request, "nvr_snapshot_removed")})


def _snap_http_response(data, status=200):
    """私有JPEG不进入共享/浏览器缓存。"""
    resp = HttpResponse(data, content_type="image/jpeg", status=status)
    resp["Cache-Control"] = "no-store"
    return resp


def _capture_snap_file(rtsp_url, snap_path, ffmpeg_cmd):
    """保留内部调用入口，安全执行由无后台依赖的快照模块完成。"""
    return capture_jpeg(rtsp_url, snap_path, ffmpeg_cmd)


def _snap_error(message, status):
    """错误不泄露命令、路径、网络地址或数据库异常。"""
    response = HttpResponse(message.encode("utf-8"), status=status, content_type="text/plain")
    response["Cache-Control"] = "no-store"
    return response


def api_openSnap(request):
    """有效登录者经数据库对象授权后才能读取/刷新快照，包括缓存命中。"""
    if request.method != "GET":
        response = _snap_error("GET required", 405)
        response["Allow"] = "GET"
        return response
    try:
        info = request.session.get("user")
        uid = info.get("id") if isinstance(info, dict) else None
        if isinstance(uid, bool) or not isinstance(uid, int) or uid <= 0:
            return _snap_error("login required", 401)
        # 不信任会话内的is_superuser标记；撤销角色/停用账户立即影响新请求。
        user = User.objects.filter(id=uid, is_active=True).first()
        if not user:
            return _snap_error("login required", 401)
        if any(len(request.GET.getlist(k)) != 1 for k in ("app", "name")):
            return _snap_error("invalid snapshot parameters", 400)
        if len(request.GET.getlist("force")) > 1 or request.GET.get("force", "0") not in ("0", "1"):
            return _snap_error("invalid snapshot parameters", 400)
        app = stream_component(request.GET.get("app"))
        name = stream_component(request.GET.get("name"))
        force = request.GET.get("force", "0") == "1"
        from app.models import StreamModel
        streams = list(StreamModel.objects.filter(app=app, name=name)[:2])
        if not streams:
            return _snap_error("stream not found", 404)
        if len(streams) != 1:
            return _snap_error("ambiguous stream", 409)
        stream = streams[0]
        if not user.is_superuser and stream.user_id != user.id:
            return _snap_error("stream access denied", 403)
        snap_dir = private_directory(settings.REBUCCA_SNAPSHOT_DIR)
        snap_path = snap_dir / ("stream-%d.jpg" % stream.id)
        with snapshot_lock(snap_dir / ("stream-%d.lock" % stream.id)) as acquired:
            if not acquired:
                return _snap_error("snapshot busy", 429)
            if not force and snap_path.exists() and 0 <= time.time() - snap_path.stat().st_mtime < 30:
                data = read_jpeg(snap_path)
                if data:
                    return _snap_http_response(data)
            rtsp_url = local_rtsp_url(stream.app, stream.name, g_config.mediaRtspPort)
            data = _capture_snap_file(rtsp_url, snap_path, settings.REBUCCA_FFMPEG_PATH)
            if not data:
                # 正常首帧延迟最多重试一次；timeout不会沿用旧缓存或无限重试。
                time.sleep(0.6)
                data = _capture_snap_file(rtsp_url, snap_path, settings.REBUCCA_FFMPEG_PATH)
            if data:
                return _snap_http_response(data)
            return _snap_error("snapshot unavailable", 502)
    except (ValueError, TypeError):
        return _snap_error("invalid snapshot input or configuration", 400)
    except subprocess.TimeoutExpired:
        return _snap_error("snapshot timeout", 504)
    except Exception:
        return _snap_error("snapshot unavailable", 500)
