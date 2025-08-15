Changelog
=========

Unreleased
----------

* Use environment variable for PostgreSQL password to prevent password leakage in logs/emails
* This repository has been transferred out of Jazzband due to logistical concerns.
* Drop support for end-of-life Python 3.7 and 3.8.
* Drop support for end-of-life Django 3.2.
* Drop support for ``DBBACKUP_STORAGE`` AND  ``DBBACKUP_STORAGE_OPTIONS`` settings, use Django's ``STORAGES['dbbackup']`` setting instead.
* Implement new ``SqliteBackupConnector`` to backup SQLite3 databases using the ``.backup`` command (safe to execute on DBs with active connections).

4.3.0 (2025-05-09)
----------

* Add generic `--pg-options` to pass custom options to postgres.
* Add option `--if-exists` for pg_dump command
* Empty string as HOST for postgres unix domain socket connection is now supported.
* Support Python 3.13 and Django 5.2

4.2.1 (2024-08-23)
----------

* Add --no-drop option to dbrestore command to prevent dropping tables before restoring data.
* Fix bug where sqlite dbrestore would fail if field data contains the line break character.

4.2.0 (2024-08-22)
------------------

* Default HOST to localhost for postgres databases.
* Add PostgreSQL Schema support
* Fix restore of database from S3 storage by reintroducing inputfile.seek(0) to utils.uncompress_file
* Add warning for filenames with slashes in them
* Fix bug where dbbackup management command would not respect settings.py:DBBACKUP_DATABASES
* Remove usage of deprecated 'get_storage_class' function in newer Django versions
* Add support for new STORAGES (Django 4.2+) setting under the 'dbbackup' alias

4.1.0 (2024-01-14)
------------------

* Fix restore fail after editing filename
* Drop python 3.6
* update links
* Update doc for backup directory consistency
* RESTORE_PREFIX for RESTORE_SUFFIX
* Support Django 4.1, 4.2 and Python 3.11
* Support Python 3.12 and Django 5.0

4.0.2 (2022-09-27)
------------------

* support for prometheus wrapped dbs
* Backup of SQLite fail if there are Virtual Tables (e.g. FTS tables).
* Closes #460: python-gnupg version increase breaks unencrypt_file func…

4.0.1 (2022-07-09)
---------------------

* As of this version, dbbackup is now within Jazzband! This version tests our Jazzband release CI, and adds miscellaneous refactoring/cleanup.
* Fix GitHub Actions configuration
* Enable functional tests in CI
* Update settings.py comment
* Jazzband transfer tasks
* Refactoring and tooling

4.0.0b0 (2021-12-19)
--------------------

* Fix RemovedInDjango41Warning related to default_app_config
* Add authentication database support for MongoDB
* Remove six dependency
* Explicitly support Python 3.6+.
* Drop support for end of life Django versions. Currently support 2.2, 3.2, 4.0.
* Replace ugettext_lazy with gettext_lazy
* Changed logging settings from settings.py to late init
* Fix authentication error when postgres is password protected
* Use exclude-table-data instead of exclude-table
* Add support for exclude tables data in the command interface
* Move author and version information into setup.py to allow building package in isolated environment (e.g. with the ``build`` package).
* Documentation fixes


3.3.0 (2020-04-14)
------------------

* Documentation fixes
* "output-filename" in mediabackup command
* Fixes for test infrastructure and mongodb support
* sqlite3: don't throw warnings if table already exists
* Fixes for django3 and updated travis (and File handling)
* Restoring from FTP
* Fixes to run dbbackup management command in Postgres for non-latin Windows.
* Apply changes from pull request 244; Update to include sftp storage
* Quick fix for proper selection of DB name to restore
