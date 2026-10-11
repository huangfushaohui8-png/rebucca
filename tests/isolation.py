"""替代有网络/线程副作用的全局初始化，视图/中间件/ORM保持真实实现。"""
import importlib
import logging
import sys
import types
from datetime import datetime
from unittest.mock import Mock, patch


def install_isolation():
    """必须在django.setup之后、视图首次导入之前执行。"""
    from app.models import StreamModel
    global_utils = types.ModuleType("app.utils.GlobalUtils")
    global_utils.g_config = types.SimpleNamespace(mediaRtspPort=10554, autoAddStreamProxy=False,
                                                 adminPort=10001, autoAddStreamProxySleep=0,
                                                 safe="legacy-test-safe")
    global_utils.g_logger = logging.getLogger("isolated.security")
    global_utils.g_session_key_user = "user"
    global_utils.g_session_key_captcha = "captcha"
    global_utils.StreamModel = StreamModel
    global_utils.datetime = datetime
    global_utils.APP_NAME_LIVE = "live"
    global_utils.APP_NAME_RTP = "rtp"
    global_utils.g_gb28181SipServer = Mock()
    global_utils.g_gb28181SipServer.request_invite.return_value = (True, "synthetic invite")
    global_utils.GlobalUtils = global_utils
    sys.modules["app.utils.GlobalUtils"] = global_utils
    # 上游InnerlView在模块导入尾部启动初始化线程；隔离套件禁止这一副作用。
    with patch("threading.Thread.start"):
        importlib.import_module("app.views.InnerlView")
    importlib.import_module("app.views.NvrView")
