import socket
import tempfile

from django.conf import settings

# Raise an exception if DBBACKUP_STORAGE or DBBACKUP_STORAGE_OPTIONS is used
if hasattr(settings, "DBBACKUP_STORAGE") or hasattr(settings, "DBBACKUP_STORAGE_OPTIONS"):
    raise RuntimeError(
        "The settings DBBACKUP_STORAGE and DBBACKUP_STORAGE_OPTIONS have been "
        "deprecated in favor of using Django Storages configuration. "
        "Please refer to the documentation for more details."
    )

DATABASES = getattr(settings, "DBBACKUP_DATABASES", list(settings.DATABASES.keys()))
HOSTNAME = getattr(settings, "DBBACKUP_HOSTNAME", socket.gethostname())
TMP_DIR = getattr(settings, "DBBACKUP_TMP_DIR", tempfile.gettempdir())
TMP_FILE_MAX_SIZE = getattr(settings, "DBBACKUP_TMP_FILE_MAX_SIZE", 10 * 1024 * 1024)
TMP_FILE_READ_SIZE = getattr(settings, "DBBACKUP_TMP_FILE_READ_SIZE", 1024 * 1000)
CLEANUP_KEEP = getattr(settings, "DBBACKUP_CLEANUP_KEEP", 10)
CLEANUP_KEEP_MEDIA = getattr(settings, "DBBACKUP_CLEANUP_KEEP_MEDIA", CLEANUP_KEEP)
CLEANUP_KEEP_FILTER = getattr(settings, "DBBACKUP_CLEANUP_KEEP_FILTER", lambda x: False)
MEDIA_PATH = getattr(settings, "DBBACKUP_MEDIA_PATH", settings.MEDIA_ROOT)
DATE_FORMAT = getattr(settings, "DBBACKUP_DATE_FORMAT", "%Y-%m-%d-%H%M%S")
FILENAME_TEMPLATE = getattr(
    settings,
    "DBBACKUP_FILENAME_TEMPLATE",
    "{databasename}-{servername}-{datetime}.{extension}",
)
MEDIA_FILENAME_TEMPLATE = getattr(settings, "DBBACKUP_MEDIA_FILENAME_TEMPLATE", "{servername}-{datetime}.{extension}")
GPG_ALWAYS_TRUST = getattr(settings, "DBBACKUP_GPG_ALWAYS_TRUST", False)
GPG_RECIPIENT = GPG_ALWAYS_TRUST = getattr(settings, "DBBACKUP_GPG_RECIPIENT", None)
STORAGES_DBBACKUP_ALIAS = "dbbackup"
DJANGO_STORAGES = getattr(settings, "STORAGES", {})
storage: dict = DJANGO_STORAGES.get(STORAGES_DBBACKUP_ALIAS, {})
STORAGE = storage.get("BACKEND", "django.core.files.storage.FileSystemStorage")
STORAGE_OPTIONS = storage.get("OPTIONS", {})
CONNECTORS = getattr(settings, "DBBACKUP_CONNECTORS", {})
CUSTOM_CONNECTOR_MAPPING = getattr(settings, "DBBACKUP_CONNECTOR_MAPPING", {})
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
SEND_EMAIL = getattr(settings, "DBBACKUP_SEND_EMAIL", True)
SERVER_EMAIL = getattr(settings, "DBBACKUP_SERVER_EMAIL", settings.SERVER_EMAIL)
ADMINS = getattr(settings, "DBBACKUP_ADMIN", settings.ADMINS)
EMAIL_SUBJECT_PREFIX = getattr(settings, "DBBACKUP_EMAIL_SUBJECT_PREFIX", "[dbbackup] ")
