# Integration tutorials

!!! note
If you have a custom and/or interesting way of using DBBackup, do not
hesitate to make a pull request.

## Django-Cron

Example recurring job using [django-cron](https://github.com/Tivix/django-cron) with filesystem storage:

```python
import os
from django.core import management
from django.conf import settings
from django_cron import CronJobBase, Schedule


class Backup(CronJobBase):
    RUN_AT_TIMES = ['6:00', '18:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'my_app.Backup'

    def do(self):
        management.call_command('dbbackup')
```

## Django-Crontab

Example crontab entry using [django-crontab](https://github.com/kraiz/django-crontab) and filesystem storage:

In `settings.py`:

```python
CRONTAB_COMMAND_SUFFIX = '2>&1'
CRONJOBS = [
    ('0 5 * * *', 'core.backup.backup_job', '>> ' + os.path.join(CORE_DIR, 'backup/backup.log'))
]
```

In `backup.py`:

```python
from datetime import datetime
from django.core import management

def backup_job():
    print("[{}] Backing up database and media files...".format(datetime.now()))
    management.call_command('dbbackup', '--clean')
    management.call_command('mediabackup', '--clean')
    print("[{}] Backup done!".format(datetime.now()))
```

Add the cron job:

```bash
python manage.py crontab add
```

### Optional: periodic verification

Consider scheduling a periodic restore test (e.g. weekly) into a throw-away
database to ensure backups remain valid:

```bash
python manage.py dbrestore --database test_restore --noinput --verbosity 1
```
