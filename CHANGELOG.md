# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
Using the following categories, list your changes in this order:
[Added, Changed, Deprecated, Removed, Fixed, Security]

Don't forget to remove deprecated code on each major release!
-->

## [Unreleased]

### Added
- Implement new `SqliteBackupConnector` to backup SQLite3 databases using the `.backup` command (safe to execute on databases with active connections).

### Changed
- This repository has been transferred out of Jazzband due to logistical concerns.

### Removed
- Drop support for end-of-life Python 3.7 and 3.8.
- Drop support for end-of-life Django 3.2.
- Drop support for `DBBACKUP_STORAGE` AND  `DBBACKUP_STORAGE_OPTIONS` settings, use Django's `STORAGES['dbbackup']` setting instead.

### Fixed
- Fix encryption support when using `gnupg==5.x`.

### Security
- Use environment variable for PostgreSQL password to prevent password leakage in logs/emails.

## [4.3.0] - 2025-05-09

### Added
- Add generic `--pg-options` to pass custom options to postgres.
- Add option `--if-exists` for `pg_dump` command.
- Support Python 3.13 and Django 5.2.

### Fixed
- Empty string as HOST for postgres unix domain socket connection is now supported.

## [4.2.1] - 2024-08-23

### Added
- Add `--no-drop` option to `dbrestore` command to prevent dropping tables before restoring data.

### Fixed
- Fix bug where sqlite `dbrestore` would fail if field data contains the line break character.

## [4.2.0] - 2024-08-22

### Added
- Add PostgreSQL Schema support.
- Add support for new `STORAGES` (Django 4.2+) setting under the 'dbbackup' alias.

### Changed
- Set postgres default database `HOST` to `"localhost"`.
- Add warning for filenames with slashes in them.

### Removed
- Remove usage of deprecated `get_storage_class` function in newer Django versions.

### Fixed
- Fix restore of database from S3 storage by reintroducing `inputfile.seek(0)` to `utils.uncompress_file`.
- Fix bug where dbbackup management commands would not respect `settings.py:DBBACKUP_DATABASES`.

## [4.1.0] - 2024-01-14

### Added
- Support Django 4.1, 4.2 and Python 3.11.
- Support Python 3.12 and Django 5.0.

### Changed
- Update documentation for backup directory consistency and update links.

### Removed
- Drop python 3.6.

### Fixed
- Fix restore fail after editing filename.
- `RESTORE_PREFIX` for `RESTORE_SUFFIX`.

## [4.0.2] - 2022-09-27

### Added
- Support for prometheus wrapped databases.

### Fixed
- Backup of SQLite fail if there are Virtual Tables (e.g. FTS tables).
- Fix broken `unencrypt_file` function in `python-gnupg`.

## [4.0.1] - 2022-07-09

### Added
- Enable functional tests in CI.

### Changed
- As of this version, dbbackup is now within Jazzband! This version tests our Jazzband release CI, and adds miscellaneous refactoring/cleanup.
- Update `settings.py` comment.
- Jazzband transfer tasks.
- Refactoring and tooling.

### Fixed
- Fix GitHub Actions configuration.

## [4.0.0b0] - 2021-12-19

### Added
- Add authentication database support for MongoDB.
- Explicitly support Python 3.6+.
- Add support for exclude tables data in the command interface.

### Changed
- Replace `ugettext_lazy` with `gettext_lazy`.
- Changed logging settings from `settings.py` to late init.
- Use `exclude-table-data` instead of `exclude-table`.
- Move author and version information into `setup.py` to allow building package in isolated environment (e.g. with the `build` package).

### Removed
- Remove six dependency.
- Drop support for end of life Django versions. Currently support 2.2, 3.2, 4.0.

### Fixed
- Fix `RemovedInDjango41Warning` related to `default_app_config`.
- Fix authentication error when postgres is password protected.
- Documentation fixes.

## [3.3.0] - 2020-04-14

### Added
- `"output-filename"` in `mediabackup` command.
- Updates to include SFTP storage.

### Fixed
- Fixes for test infrastructure and mongodb support.
- sqlite3: don't throw warnings if table already exists.
- Fixes for django v3 and update travis.
- Restoring from FTP.
- Fix management commands when using Postgres on non-latin Windows.
- Fix improper database name selection when performing a restore.

[Unreleased]: https://github.com/Archmonger/django-dbbackup/compare/v4.3.0...HEAD
[4.3.0]: https://github.com/Archmonger/django-dbbackup/compare/v4.2.1...v4.3.0
[4.2.1]: https://github.com/Archmonger/django-dbbackup/compare/v4.2.0...v4.2.1
[4.2.0]: https://github.com/Archmonger/django-dbbackup/compare/v4.1.0...v4.2.0
[4.1.0]: https://github.com/Archmonger/django-dbbackup/compare/v4.0.2...v4.1.0
[4.0.2]: https://github.com/Archmonger/django-dbbackup/compare/v4.0.1...v4.0.2
[4.0.1]: https://github.com/Archmonger/django-dbbackup/compare/v4.0.0b0...v4.0.1
[4.0.0b0]: https://github.com/Archmonger/django-dbbackup/compare/v3.3.0...v4.0.0b0
[3.3.0]: https://github.com/Archmonger/django-dbbackup/releases/tag/3.3.0
