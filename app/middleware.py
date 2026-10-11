# 官网：https://www.yuturuishi.com
# 微信：yuturuishi
# gitee开源地址：https://gitee.com/yuturuishi/rebucca
# github开源地址：https://github.com/yuturuishi/rebucca
from django.http import HttpResponseRedirect
from app.security import authenticate_callback, boundary_error

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object

# 无需登录即可访问的路径前缀（精确控制，禁止 blanket /open/ 放行）
AUTH_WHITELIST_PREFIXES = (
    '/login',
    '/logout',
    '/user/openCaptcha',
    '/static/',
)

class SimpleMiddleware(MiddlewareMixin):
    def process_request(self, request):
        """敏感入口先执行独立边界，不能被公共前缀/会话/旧Safe放行。"""
        path = request.path_info

        if path.startswith('/inner/'):
            return authenticate_callback(request)
        if path in ('/nvr/openSnap', '/nvr/openSnapShot'):
            if not request.session.get("user"):
                return boundary_error("login required", 401)
            # 用户有效性和流对象权限由实际截图视图从数据库重新判定。
            return None

        for prefix in AUTH_WHITELIST_PREFIXES:
            if path.startswith(prefix):
                return None

        if request.session.has_key("user"):
            if path.startswith("/login"):
                return HttpResponseRedirect("/")
            return None

        # 未登录：open API 须带 Safe 头（config.json safe 字段）
        if '/open' in path:
            headers = request.headers
            safe = headers.get("Safe") or request.META.get("HTTP_SAFE")
            try:
                from app.utils.GlobalUtils import g_config
                if safe and safe == g_config.safe:
                    return None
            except Exception:
                pass
            return HttpResponseRedirect("/login")

        return HttpResponseRedirect("/login")

    def process_response(self, request, response):
        return response
