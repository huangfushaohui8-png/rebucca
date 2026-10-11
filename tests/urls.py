"""只将四个真实回调和真实截图映射到测试客户端，不加载其他产品视图。"""
from django.http import HttpResponse
from django.urls import path
from app.views import NvrView, InnerlView


def public_probe(request):
    """验证既有公开入口及登录后路由没有被本轮全局封锁。"""
    return HttpResponse("synthetic route")


urlpatterns = [
    path("nvr/openSnap", NvrView.api_openSnap),
    path("inner/on_media_update_stream", InnerlView.api_on_media_update_stream),
    path("inner/on_media_delete_stream", InnerlView.api_on_media_delete_stream),
    path("inner/on_publish", InnerlView.api_on_publish),
    path("inner/on_stream_not_found", InnerlView.api_on_stream_not_found),
    path("login", public_probe), path("user/openCaptcha", public_probe),
    path("stream/index", public_probe),
]
