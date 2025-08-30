"""Apps for DBBackup"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy

from dbbackup import log


class DbbackupConfig(AppConfig):
    """
    Config for DBBackup application.
    """

    name = "dbbackup"
    label = "dbbackup"
    verbose_name = gettext_lazy("Backup and restore")
    default_auto_field = "django.db.models.AutoField"

    def ready(self):
        log.load()
