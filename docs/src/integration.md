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

## Django-Celery-Beat

Example setup using [Celery](https://docs.celeryq.dev/) with [django-celery-beat](https://django-celery-beat.readthedocs.io/) for scheduled backups:

First, create a `tasks.py` file in your app:

```python
from celery import Celery
from django.core import management

app = Celery()


@app.task
def backup_db():
    management.call_command('dbbackup')


@app.task
def backup_media():
    management.call_command('mediabackup')
```

Then, create a Django management command to set up periodic tasks (e.g., `management/commands/setup_backup_schedule.py`):

```python
from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask
import pytz


class Command(BaseCommand):
    help = 'Creates crontab schedule objects and periodic tasks that use them'

    def handle(self, *args, **options):
        # Schedule for daily backups at midnight UTC
        every_day, _ = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='0',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone=pytz.timezone('UTC')
        )

        # Create periodic tasks
        PeriodicTask.objects.get_or_create(
            crontab=every_day,
            name='Backup DB',
            task='myapp.tasks.backup_db',
        )

        PeriodicTask.objects.get_or_create(
            crontab=every_day,
            name='Backup Media',
            task='myapp.tasks.backup_media',
        )

        self.stdout.write(
            self.style.SUCCESS('Successfully created backup schedule')
        )
```

Run the setup command:

```bash
python manage.py setup_backup_schedule
```

Make sure your Celery worker and beat scheduler are running:

```bash
celery -A myproject worker --loglevel=info
celery -A myproject beat --loglevel=info
```

## Periodic Verification

Consider scheduling a periodic restore test (e.g. weekly) into a throw-away
database to ensure your backup or filesystem remains valid:

```bash
python manage.py dbrestore --database test_restore --noinput --verbosity 1
```
