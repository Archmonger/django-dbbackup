"""
Configuration and launcher for dbbackup tests.
"""

import os
import sys

from dotenv import load_dotenv

test = len(sys.argv) <= 1 or sys.argv[1] == "test"
if not test:
    load_dotenv()

DEBUG = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Use a repository local tmp directory instead of system /tmp to improve
# cross-platform compatibility (especially on Windows) and to avoid
# permission or cleanup issues on shared CI runners.
REPO_TMP_DIR = os.path.join(BASE_DIR, "..", "tmp")
os.makedirs(REPO_TMP_DIR, exist_ok=True)
TESTAPP_DIR = os.path.join(BASE_DIR, "testapp/")
BLOB_DIR = os.path.join(TESTAPP_DIR, "blobs/")

ADMINS = (("ham", "foo@bar"),)
ALLOWED_HOSTS = ["*"]
MIDDLEWARE_CLASSES = ()
ROOT_URLCONF = "tests.testapp.urls"
SECRET_KEY = "it's a secret to everyone"
SITE_ID = 1
MEDIA_ROOT = os.environ.get("MEDIA_ROOT") or os.path.join(REPO_TMP_DIR, "media")
os.makedirs(MEDIA_ROOT, exist_ok=True)
INSTALLED_APPS = (
    "dbbackup",
    "tests.testapp",
)
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.sqlite3"),
        # Default DB file stored inside repository tmp directory
        "NAME": os.environ.get("DB_NAME", os.path.join(REPO_TMP_DIR, "test_db.sqlite3")),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT"),
    }
}
if os.environ.get("CONNECTOR"):
    CONNECTOR = {"CONNECTOR": os.environ["CONNECTOR"]}
    DBBACKUP_CONNECTORS = {"default": CONNECTOR}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

SERVER_EMAIL = "dbbackup@test.org"
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

DBBACKUP_GPG_RECIPIENT = "test@test"
DBBACKUP_GPG_ALWAYS_TRUST = (True,)

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {},
    },
    "dbbackup": {
        "BACKEND": os.environ.get("STORAGE", "tests.utils.FakeStorage"),
        "OPTIONS": dict([
            keyvalue.split("=") for keyvalue in os.environ.get("STORAGE_OPTIONS", "").split(",") if keyvalue
        ]),
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "root": {"handlers": ["console"], "level": "DEBUG"},
    "handlers": {
        "console": {
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "class": "logging.StreamHandler",
            "formatter": "simple",
        }
    },
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            "datefmt": "%d/%b/%Y %H:%M:%S",
        },
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "loggers": {
        "django.db.backends": {
            # uncomment to see all queries
            # 'level': 'DEBUG',
            "handlers": ["console"],
        }
    },
}

# let there be silence
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
