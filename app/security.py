"""F01/F02 的确定性输入和服务身份边界；导入时不启动任何后台服务。"""
import configparser
import functools
import hmac
import ipaddress
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.http import JsonResponse

CALLBACK_SERVICES = {
    "/inner/on_media_update_stream": "sip",
    "/inner/on_media_delete_stream": "sip",
    "/inner/on_publish": "zlm",
    "/inner/on_stream_not_found": "zlm",
}
MAX_CALLBACK_BYTES = 64 * 1024
_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,49}\Z")
_TOKEN = re.compile(r"[0-9a-f]{64}\Z")


def stream_component(value):
    """保留常用 ZLM/GB28181 标识；拒绝路径、控制字符、shell 和 URL 分隔符。"""
    if not isinstance(value, str) or not _COMPONENT.fullmatch(value):
        raise ValueError("invalid stream identifier")
    return value


def boundary_error(message, status):
    """ZLM 失败必须返回非零 code；错误不包含秘密或原始输入。"""
    response = JsonResponse({"code": -1, "msg": message}, status=status)
    response["Cache-Control"] = "no-store"
    return response


def service_token(service):
    """从运行环境取得独立32字节秘密；禁止空配置、示例凭据和两服务共用。"""
    tokens = {s: os.environ.get("REBUCCA_%s_CALLBACK_TOKEN" % s.upper(), "")
              for s in ("sip", "zlm")}
    if service not in tokens or any(not _TOKEN.fullmatch(t) for t in tokens.values()):
        raise ValueError("callback credentials not configured")
    if hmac.compare_digest(tokens["sip"], tokens["zlm"]):
        raise ValueError("callback credentials must be distinct")
    return tokens[service]


def authenticate_callback(request, expected_service=None):
    """实际对端、精确路由和独立秘密共同鉴权；会话和旧 Safe 不作为服务身份。"""
    service = CALLBACK_SERVICES.get(request.path_info)
    if not service or (expected_service and service != expected_service):
        return boundary_error("callback not found", 404)
    if request.method != "POST":
        response = boundary_error("POST required", 405)
        response["Allow"] = "POST"
        return response
    try:
        peer = ipaddress.ip_address(request.META.get("REMOTE_ADDR", ""))
    except ValueError:
        return boundary_error("callback peer denied", 403)
    # 不信任代理宣称的来源，也不允许公网代理借回环地址注入服务回调。
    if not peer.is_loopback or any(request.META.get(k) for k in
                                  ("HTTP_FORWARDED", "HTTP_X_FORWARDED_FOR", "HTTP_X_REAL_IP")):
        return boundary_error("callback peer denied", 403)
    try:
        expected = service_token(service)
    except ValueError:
        return boundary_error("callback credentials unavailable", 503)
    authorization = request.headers.get("Authorization", "")
    query_tokens = request.GET.getlist("callback_token")
    if authorization:
        if (query_tokens or request.headers.get("X-Rebucca-Service") != service
                or not authorization.startswith("Bearer ")):
            return boundary_error("callback identity denied", 401)
        supplied = authorization[len("Bearer "):]
    else:
        # 原生 ZLM hook 无自定义鉴权头：仅其两个精确路由支持运行时 URL token。
        if service != "zlm" or len(query_tokens) != 1:
            return boundary_error("callback identity required", 401)
        supplied = query_tokens[0]
    if not _TOKEN.fullmatch(supplied) or not hmac.compare_digest(supplied, expected):
        return boundary_error("callback identity denied", 401)
    return None


def _integer(params, key, default=0, minimum=0, maximum=2**63 - 1):
    """兼容十进制字符串和JSON整数，拒绝bool、负数、超界与截断浮点数。"""
    value = params.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError("invalid numeric field")
    if isinstance(value, str) and not re.fullmatch(r"[0-9]{1,19}", value):
        raise ValueError("invalid numeric field")
    if not minimum <= int(value) <= maximum:
        raise ValueError("numeric field out of range")


def validate_callback_payload(path, params):
    """在持久化/删除/设备邀请之前验证回调的相关字段和协议范围。"""
    if not isinstance(params, dict):
        raise ValueError("JSON object required")
    if path.endswith("on_media_delete_stream"):
        stream_component(params.get("code"))
        return
    app = stream_component(params.get("app"))
    name_key = "name" if path.endswith("on_media_update_stream") else "stream"
    stream_component(params.get(name_key))
    if path.endswith("on_media_update_stream"):
        if app != "rtp" or params.get("pullStreamType") not in (21, "21"):
            raise ValueError("unsupported SIP stream")
        _integer(params, "forwardState", maximum=1)
        for field in ("port", "rtpServerPort", "rtpPort"):
            _integer(params, field, maximum=65535)
        for field in ("lastKeepaliveTime", "lastRegisterTime"):
            # datetime.fromtimestamp 兼容到2100年；避免平台时间转换溢出。
            _integer(params, field, maximum=4102444800000)
        _integer(params, "cameraSumNum", default=1, maximum=100000)
        _integer(params, "rtpTransferMode", maximum=2)
        _integer(params, "rtpTransferAudioType", maximum=1)
        ipaddress.ip_address(params.get("ip", ""))
        stream_component(params.get("clientId"))
        if params.get("pullStreamUrl") != "rtp://__":
            raise ValueError("unsupported SIP source")
        for field in ("cameraName", "cameraManufacturer", "cameraModel", "cameraOwner",
                      "cameraCivilCode", "parentID"):
            value = params.get(field, "")
            if (not isinstance(value, str) or len(value) > 100
                    or any(ord(c) < 32 for c in value)):
                raise ValueError("invalid device text")
    else:
        if app not in ("live", "rtp"):
            raise ValueError("unsupported ZLM app")
        if path.endswith("on_publish"):
            if params.get("schema") not in ("rtsp", "rtmp"):
                raise ValueError("unsupported publish schema")
            ipaddress.ip_address(params.get("ip", ""))
            _integer(params, "port", maximum=65535)
            value = params.get("id", "")
            if not isinstance(value, str) or len(value) > 100 or any(ord(c) < 32 for c in value):
                raise ValueError("invalid publisher id")


def _unique_json_object(pairs):
    """拒绝JSON重复键，避免不同组件对同一凭据/对象参数作不同解释。"""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def require_callback_service(service):
    """视图自身强制鉴权和有限JSON解析，中间件遗漏也不能绕过。"""
    def decorate(view):
        @functools.wraps(view)
        def wrapped(request, *args, **kwargs):
            error = authenticate_callback(request, service)
            if error is not None:
                return error
            if request.content_type != "application/json":
                return boundary_error("JSON required", 415)
            try:
                length = int(request.META.get("CONTENT_LENGTH") or 0)
                if length < 0 or length > MAX_CALLBACK_BYTES:
                    return boundary_error("callback body too large", 413)
                # 限量读取避免上游1.5GB全局body限制被这个小回调继承。
                raw = request.read(MAX_CALLBACK_BYTES + 1)
                if len(raw) > MAX_CALLBACK_BYTES:
                    return boundary_error("callback body too large", 413)
                params = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_json_object)
                validate_callback_payload(request.path_info, params)
            except (ValueError, TypeError, UnicodeError):
                return boundary_error("invalid callback payload", 400)
            request.callback_payload = params
            return view(request, *args, **kwargs)
        return wrapped
    return decorate


def sip_callback_headers(url):
    """凭据仅发到本机精确SIP回调，禁止交给重定向或任意admin_host。"""
    parsed = urlsplit(url)
    try:
        local = ipaddress.ip_address(parsed.hostname or "").is_loopback
    except ValueError:
        local = False
    if (not local or parsed.scheme != "http" or parsed.username or parsed.password
            or parsed.query or parsed.fragment or CALLBACK_SERVICES.get(parsed.path) != "sip"):
        raise ValueError("invalid SIP callback destination")
    return {"Content-Type": "application/json", "X-Rebucca-Service": "sip",
            "Authorization": "Bearer " + service_token("sip")}


def private_directory(path):
    """私有缓存/运行配置不得位于仓库公共static目录。"""
    directory = Path(path).resolve()
    public = (Path(settings.BASE_DIR) / "static").resolve()
    if directory == public or public in directory.parents:
        raise ValueError("private directory cannot be under static")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    return directory


def prepare_zlm_callback_config(source, admin_port):
    """保留媒体参数，生成0600临时hook配置；秘密不写原配置或日志。"""
    port = int(admin_port)
    if not 1 <= port <= 65535:
        raise ValueError("invalid callback port")
    token = service_token("zlm")
    config = configparser.ConfigParser(interpolation=None)
    # 上游INI含GBK注释，ZLM键区分大小写；不能让ConfigParser静默改写媒体参数。
    config.optionxform = str
    raw = Path(source).read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("gb18030")
    config.read_string(text)
    if not config.has_section("hook"):
        config.add_section("hook")
    config.set("hook", "enable", "1")
    for route in ("on_publish", "on_stream_not_found"):
        config.set("hook", route, "http://127.0.0.1:%d/inner/%s?%s" %
                   (port, route, urlencode({"callback_token": token})))
    directory = private_directory(getattr(settings, "REBUCCA_PRIVATE_RUNTIME_DIR",
                                          Path(settings.BASE_DIR) / "var" / "runtime"))
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix="zlm-", suffix=".ini",
                                     dir=directory, delete=False) as file:
        os.chmod(file.name, 0o600)
        config.write(file)
        return file.name
