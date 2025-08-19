# Django Signals Support

Django-dbbackup now supports Django signals that allow you to hook into backup and restore operations to perform custom actions.

## Available Signals

The following signals are available. Each provide different arguments depending on the operation.

---

### Database Backup Signals

---

**pre_backup** (`dbbackup.signals.pre_backup`)

Sent before a database backup starts.

| Parameter    | Description                           |
| ------------ | ------------------------------------- |
| `sender`     | The command class (`DbBackupCommand`) |
| `database`   | Database configuration dict           |
| `connector`  | Database connector instance           |
| `servername` | Server name for the backup            |

---

**post_backup** (`dbbackup.signals.post_backup`)

Sent after a database backup completes.

| Parameter    | Description                           |
| ------------ | ------------------------------------- |
| `sender`     | The command class (`DbBackupCommand`) |
| `database`   | Database configuration dict           |
| `connector`  | Database connector instance           |
| `servername` | Server name for the backup            |
| `filename`   | Generated backup filename             |
| `storage`    | Storage backend instance              |

---

### Database Restore Signals

---

**pre_restore** (`dbbackup.signals.pre_restore`)

Sent before a database restore starts.

| Parameter       | Description                            |
| --------------- | -------------------------------------- |
| `sender`        | The command class (`DbRestoreCommand`) |
| `database`      | Database configuration dict            |
| `database_name` | Name of the database being restored    |
| `filename`      | Backup filename being restored         |
| `servername`    | Server name                            |
| `storage`       | Storage backend instance               |

---

**post_restore** (`dbbackup.signals.post_restore`)

Sent after a database restore completes.

| Parameter       | Description                            |
| --------------- | -------------------------------------- |
| `sender`        | The command class (`DbRestoreCommand`) |
| `database`      | Database configuration dict            |
| `database_name` | Name of the database being restored    |
| `filename`      | Backup filename being restored         |
| `servername`    | Server name                            |
| `connector`     | Database connector instance            |
| `storage`       | Storage backend instance               |

---

### Media Backup Signals

---

**pre_media_backup** (`dbbackup.signals.pre_media_backup`)

Sent before a media backup starts.

| Parameter    | Description                              |
| ------------ | ---------------------------------------- |
| `sender`     | The command class (`MediaBackupCommand`) |
| `servername` | Server name for the backup               |
| `storage`    | Storage backend instance                 |

---

**post_media_backup** (`dbbackup.signals.post_media_backup`)

Sent after a media backup completes.

| Parameter    | Description                              |
| ------------ | ---------------------------------------- |
| `sender`     | The command class (`MediaBackupCommand`) |
| `filename`   | Generated backup filename                |
| `servername` | Server name for the backup               |
| `storage`    | Storage backend instance                 |

---

### Media Restore Signals

---

**pre_media_restore** (`dbbackup.signals.pre_media_restore`)

Sent before a media restore starts.

| Parameter    | Description                               |
| ------------ | ----------------------------------------- |
| `sender`     | The command class (`MediaRestoreCommand`) |
| `filename`   | Backup filename being restored            |
| `servername` | Server name                               |
| `storage`    | Storage backend instance                  |

---

**post_media_restore** (`dbbackup.signals.post_media_restore`)

Sent after a media restore completes.

| Parameter    | Description                               |
| ------------ | ----------------------------------------- |
| `sender`     | The command class (`MediaRestoreCommand`) |
| `filename`   | Backup filename being restored            |
| `servername` | Server name                               |
| `storage`    | Storage backend instance                  |

---

## Usage Examples

### Basic Signal Handler

```python
from django.dispatch import receiver
from dbbackup import signals

@receiver(signals.pre_backup)
def backup_started(sender, database, **kwargs):
    print(f"Starting backup of database: {database['NAME']}")

@receiver(signals.post_backup)
def backup_completed(sender, database, filename, **kwargs):
    print(f"Completed backup of {database['NAME']} to {filename}")
```

### Notification System

```python
from django.dispatch import receiver
from django.core.mail import send_mail
from dbbackup import signals

@receiver(signals.post_backup)
def notify_backup_complete(sender, database, filename, **kwargs):
    send_mail(
        subject='Database Backup Complete',
        message=f'Successfully backed up {database["NAME"]} to {filename}',
        from_email='backup@example.com',
        recipient_list=['admin@example.com'],
    )

@receiver(signals.post_restore)
def notify_restore_complete(sender, database_name, filename, **kwargs):
    send_mail(
        subject='Database Restore Complete',
        message=f'Successfully restored {database_name} from {filename}',
        from_email='backup@example.com',
        recipient_list=['admin@example.com'],
    )
```

### Logging and Monitoring

```python
import logging
from django.dispatch import receiver
from dbbackup import signals

logger = logging.getLogger(__name__)

@receiver(signals.pre_backup)
def log_backup_start(sender, database, **kwargs):
    logger.info(f"Starting backup process for {database['NAME']}")

@receiver(signals.post_backup)
def log_backup_complete(sender, database, filename, **kwargs):
    logger.info(f"Backup process completed for {database['NAME']}, file: {filename}")

@receiver(signals.pre_restore)
def log_restore_start(sender, database_name, filename, **kwargs):
    logger.warning(f"Starting restore process for {database_name} from {filename}")

@receiver(signals.post_restore)
def log_restore_complete(sender, database_name, **kwargs):
    logger.info(f"Restore process completed for {database_name}")
```

### Custom Validation

```python
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from dbbackup import signals

@receiver(signals.pre_restore)
def validate_restore_conditions(sender, database_name, **kwargs):
    # Add custom validation logic
    if database_name == 'production' and not user_has_permission():
        raise ValidationError("Restore not allowed for production database")
```

### Integration with External Services

```python
from django.dispatch import receiver
from dbbackup import signals
import requests

@receiver(signals.post_backup)
def webhook_notification(sender, database, filename, **kwargs):
    # Send webhook to external monitoring service
    requests.post('https://monitoring.example.com/webhook', json={
        'event': 'backup_complete',
        'database': database['NAME'],
        'filename': filename,
        'timestamp': timezone.now().isoformat(),
    })
```

## Registration

Make sure your signal handlers are imported when Django starts up. The best place is usually in your app's `apps.py` file:

```python
from django.apps import AppConfig

class YourAppConfig(AppConfig):
    name = 'your_app'

    def ready(self):
        import your_app.signals  # Import your signal handlers
```

Or in your app's `__init__.py`:

```python
default_app_config = 'your_app.apps.YourAppConfig'
```
