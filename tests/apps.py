"""隔离AppConfig只注册真实ORM模型，不调用上游ready副作用。"""
from django.apps import AppConfig


class IsolatedAppConfig(AppConfig):
    """保留真实模型映射，禁用SIP/分析/媒体启动和自动schema升级。"""
    name = "app"
    default_auto_field = "django.db.models.BigAutoField"
