<!--docs-top-start-->

# Django DBBackup

<p>
    <a href="https://github.com/Archmonger/django-dbbackup/actions">
        <img src="https://github.com/Archmonger/django-dbbackup/actions/workflows/ci.yml/badge.svg">
    </a>
    <a href="https://pypi.python.org/pypi/django-dbbackup">
        <img src="https://img.shields.io/pypi/v/django-dbbackup.svg?label=PyPI">
    </a>
    <a href="https://github.com/Archmonger/django-dbbackup/blob/master/LICENSE.md">
        <img src="https://img.shields.io/badge/License-BSD-purple.svg">
    </a>
    <a href="https://archmonger.github.io/django-dbbackup/">
        <img alt="Website" src="https://img.shields.io/website?url=https%3A%2F%2Farchmonger.github.io%2Fdjango-dbbackup%2F&up_message=online&down_message=offline&logo=readthedocs&logoColor=white&label=docs">
    </a>
</p>

This Django application provides management commands to help backup and restore your project database and media files with various storages such as Amazon S3, Dropbox, local file storage, or any Django-supported storage.

The main features include:

-   Secure your backup with GPG signature and encryption.
-   Archive with compression.
-   Easily manage remote archiving.
-   Keep your development database up to date.
-   Set up automated backups with Crontab or Celery.
-   Manually backup and restore via Django management commands.

<!--docs-top-end-->

For more details, see the [official documentation](https://archmonger.github.io/django-dbbackup/).

<!--docs-bottom-start-->

## Why use DBBackup?

DBBackup gives you a simple yet robust interface to backup, encrypt, transmit, and restore your database and media.

In a few words, it is a pipe between your Django project and your backups. It is written to be far more efficient than Django's [backup](https://docs.djangoproject.com/en/stable/ref/django-admin/#dumpdata)/[restore](https://docs.djangoproject.com/en/stable/ref/django-admin/#loaddata) commands by using your database's native/standard/best procedure(s) or tool(s) to perform backups.

Ultimately, this helps simplify the task of "creating a backup" by removing the need for writing relational query commands, using complex tools, or creating scripts. Optionally, DBBackup can apply compression and/or encryption before transferring the data to nearly any storage system.

<!--docs-bottom-end-->
