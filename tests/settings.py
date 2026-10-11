"""隔离Django设置：新建测试库、私有临时缓存、无现成业务数据库。"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TEST_ROOT = Path(os.environ["REBUCCA_TEST_ROOT"])
SECRET_KEY = os.urandom(32).hex()
DEBUG = False
ALLOWED_HOSTS = ["testserver", "127.0.0.1"]
INSTALLED_APPS = ["django.contrib.auth", "django.contrib.contenttypes",
                  "django.contrib.sessions", "tests.apps.IsolatedAppConfig"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3",
                         "NAME": str(TEST_ROOT / "empty.sqlite3")}}
MIDDLEWARE = ["django.contrib.sessions.middleware.SessionMiddleware",
              "app.middleware.SimpleMiddleware"]
ROOT_URLCONF = "tests.urls"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = False
LANGUAGE_CODE = "zh-hans"
REBUCCA_SNAPSHOT_DIR = str(TEST_ROOT / "snapshots")
REBUCCA_PRIVATE_RUNTIME_DIR = str(TEST_ROOT / "runtime")
REBUCCA_FFMPEG_PATH = "/usr/bin/ffmpeg"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # 仅合成测试账户
