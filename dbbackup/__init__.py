"""Management commands to help backup and restore a project database and media"""

import django

__version__ = "4.3.0"

if django.VERSION < (3, 2):
    default_app_config = "dbbackup.apps.DbbackupConfig"
