Django Database Backup
======================

.. image:: https://github.com/Archmonger/django-dbbackup/actions/workflows/build.yml/badge.svg
        :target: https://github.com/Archmonger/django-dbbackup/actions

.. image:: https://readthedocs.org/projects/django-dbbackup/badge/?version=stable
        :target: https://django-dbbackup.readthedocs.io/
        :alt: Documentation Status

This Django application provides management commands to help backup and
restore your project database and media files with various storages such as
Amazon S3, Dropbox, local file storage or any Django storage.

It is made to:

- Allow you to secure your backup with GPG signature and encryption
- Archive with compression
- Deal easily with remote archiving
- Keep your development database up to date
- Use Crontab or Celery to setup automated backups
- Manually backup and restore via Django management commands

Docs
====

See our official documentation at `Read The Docs`_.

Why use DBBackup
================

This software doesn't reinvent the wheel, in a few words it is a pipe between
your Django project and your backup storage. It tries to use database native (non-Django) dump &
restore mechanisms, apply compression and/or encryption and use the storage system you desire.

It gives a simple interface to backup and restore your database or media
files.

Contributing
============

All contribution are very welcomed, propositions, problems, bugs and
enhancement are tracked with `GitHub issues`_ system and patches are submitted
via `pull requests`_.

We use GitHub Actions as continuous integration tools.

.. _`Read The Docs`: https://django-dbbackup.readthedocs.org/
.. _`GitHub issues`: https://github.com/Archmonger/django-dbbackup/issues
.. _`pull requests`: https://github.com/Archmonger/django-dbbackup/pulls
