.. building docs: cd django-dbbackup/docs && make html

Django Database Backup
======================

This Django application provides management commands to help backup and
restore your project database and media files with various storages such as
Amazon S3, DropBox or local file system.

It is made to:

- Allow you to secure your backup with GPG signature and encryption
- Archive with compression
- Deal easily with remote archiving
- Keep your development database up to date
- Use Crontab or Celery to setup automated backups

Contents:

.. toctree::
   :maxdepth: 1

   installation
   configuration
   databases
   storage
   commands
   integration
   contributing
   changelog

Other Resources
===============

* `GitHub repository`_
* `PyPI project`_
* `Read The Docs`_
* `GitHub issues`_
* `GitHub pull requests`_
* `Coveralls`_

.. _`GitHub repository`: https://github.com/Archmonger/django-dbbackup
.. _`PyPI project`: https://pypi.python.org/pypi/django-dbbackup/
.. _`Read The Docs`: https://django-dbbackup.readthedocs.org/
.. _`GitHub issues`: https://github.com/Archmonger/django-dbbackup/issues
.. _`GitHub pull requests`: https://github.com/Archmonger/django-dbbackup/pulls
.. _`Coveralls`: https://coveralls.io/github/Archmonger/django-dbbackup

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
