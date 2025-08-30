"""
Django signals for dbbackup operations.

These signals allow users to hook into the backup and restore process
to perform custom actions before and after backup/restore operations.
"""

import django.dispatch

# Database backup signals
pre_backup = django.dispatch.Signal()
post_backup = django.dispatch.Signal()

# Database restore signals
pre_restore = django.dispatch.Signal()
post_restore = django.dispatch.Signal()

# Media backup signals
pre_media_backup = django.dispatch.Signal()
post_media_backup = django.dispatch.Signal()

# Media restore signals
pre_media_restore = django.dispatch.Signal()
post_media_restore = django.dispatch.Signal()
