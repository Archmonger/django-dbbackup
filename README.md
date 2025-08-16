# Django Database Backup

[![Build Status](https://github.com/Archmonger/django-dbbackup/actions/workflows/build.yml/badge.svg)](https://github.com/Archmonger/django-dbbackup/actions)

This Django application provides management commands to help backup and restore your project database and media files with various storages such as Amazon S3, Dropbox, local file storage, or any Django-supported storage.

## Features

-   Secure your backup with GPG signature and encryption.
-   Archive with compression.
-   Easily manage remote archiving.
-   Keep your development database up to date.
-   Set up automated backups with Crontab or Celery.
-   Manually backup and restore via Django management commands.

## Documentation

For more details, see the [official documentation](https://archmonger.github.io/django-dbbackup/).

## Why use DBBackup?

This software doesn't reinvent the wheel. In a few words, it is a pipe between your Django project and your backup storage. It uses native database dump and restore mechanisms (non-Django), applies compression and/or encryption, and works with your desired storage system.

It provides a simple interface to backup and restore your database or media files.

## Contributing

All contributions are very welcome. Propositions, problems, bugs, and enhancements are tracked with [GitHub issues](https://github.com/Archmonger/django-dbbackup/issues), and patches are submitted via [pull requests](https://github.com/Archmonger/django-dbbackup/pulls).

We use GitHub Actions for continuous integration.
