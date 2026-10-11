"""可复现测试入口，退出码表示实际套件结果；不使用manage.py或样例数据库。"""
import os
import secrets
import sys
import tempfile


def main():
    """只用当前进程生成合成服务token，临时目录在运行结束后清理。"""
    with tempfile.TemporaryDirectory(prefix="rebucca-security-") as directory:
        os.environ["REBUCCA_TEST_ROOT"] = directory
        os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings"
        os.environ["REBUCCA_SIP_CALLBACK_TOKEN"] = secrets.token_hex(32)
        os.environ["REBUCCA_ZLM_CALLBACK_TOKEN"] = secrets.token_hex(32)
        import django
        django.setup()
        from tests.isolation import install_isolation
        install_isolation()
        from django.test.runner import DiscoverRunner
        runner = DiscoverRunner(verbosity=2)
        return runner.run_tests(["tests.test_security"])


if __name__ == "__main__":
    sys.exit(bool(main()))
