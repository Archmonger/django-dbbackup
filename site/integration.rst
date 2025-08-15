Integration tutorials
=====================

.. note::

    If you have a custom and/or interesting way of use DBBackup, do not
    hesitate to make a pull request.

Django-cron
-----------

Example of cron job with `django-cron`_  with file system storage: ::

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

.. _`django-cron`: https://github.com/Tivix/django-cron

Django-crontab
--------------

Example of cron job with `django-crontab`_ with file system storage:

In `settings.py`: ::

  CRONTAB_COMMAND_SUFFIX = '2>&1'
  CRONJOBS = [
      ('0 5 * * *', 'core.backup.backup_job', '>> ' + os.path.join(CORE_DIR, 'backup/backup.log'))
  ]

In `backup.py`: ::

  from datetime import datetime
  from django.core import management
  
  def backup_job():
      print("[{}] Backing up database and media files...".format(datetime.now()))
      management.call_command('dbbackup', '--clean')
      management.call_command('mediabackup', '--clean')
      print("[{}] Backup done!".format(datetime.now()))


To add the cron job: ::

  python manage.py crontab add

.. _`django-crontab`: https://github.com/kraiz/django-crontab
