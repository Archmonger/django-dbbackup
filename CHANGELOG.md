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
- Verified full Windows compatibility via new CI workflows.

### Changed

- This repository has been transferred out of Jazzband due to logistical concerns.

### Removed

- Drop support for end-of-life Python 3.7 and 3.8.
- Drop support for end-of-life Django 3.2.
- Drop support for `DBBACKUP_STORAGE` AND `DBBACKUP_STORAGE_OPTIONS` settings, use Django's `STORAGES['dbbackup']` setting instead.

### Fixed

- Fix encryption support when using `gnupg==5.x`.
- Resolve SQLite backup temporary file locking issues on Windows.

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

- Support Python 3.11 and 3.12.
- Support Django 4.1, 4.2, and 5.0.

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

## [3.2.0] - 2017-09-18

### Added

- `PgDumpBinaryConnector` (binary `pg_dump` integration) with related functional tests.
- Option to keep specific old backups (custom clean old backups logic).

### Changed

- Updated PostgreSQL documentation and help text for clarity.

### Fixed

- SFTP storage file attribute error ("SFTPStorageFile object has no attribute name").
- Escaping of passwords passed to commands.
- Corrected management command help text after flag logic change.

## [3.1.3] - 2016-11-25

### Fixed

- Reverted a regression in `pg_dump` database name handling introduced shortly before.

## [3.1.2] - 2016-11-25

### Fixed

- Correct `pg_dump` invocation: proper username and database argument handling.

## [3.1.1] - 2016-11-16

### Fixed

- Unicode handling issues with SQLite backups.

## [3.1.0] - 2016-11-15

### Added

- Support for inheriting parent environment variables in command connectors (`USE_PARENT_ENV`).

### Changed

- Complete revamp of logging and error email notification system (more structured logging & tests).

## [3.0.4] - 2016-11-14

### Added

- Ability to link / register custom connectors.

### Changed

- Use naïve (timezone-unaware) `datetime` in backup filenames for broader compatibility.

### Fixed

- `mediabackup` timeout issue.
- Improved PostgreSQL `dbrestore` error recognition.

## [3.0.3] - 2016-09-15

### Added

- Server name filter for database and media backup/restore.
- Ability to select multiple databases for backup.

### Changed

- Improved filename generation logic.

### Fixed

- Database filter logic and clean backup behavior.

## [3.0.2] - 2016-08-06

### Fixed

- Disabled Django loggers inadvertently affecting application logging.

## [3.0.1] - 2016-08-04

### Added

- New connector architecture with dedicated connectors for PostgreSQL, MySQL, SQLite (copy) and MongoDB.
- Media backup & restore system overhaul (per-file processing, media restore command & tests).
- Exclude table/data options, prefix & suffix options for connector commands.
- Environment variable control for command execution.
- GIS database engine mapping support.
- Functional, integration and upgrade test suites; app & system checks integration.

### Changed

- Refactored and unified code between database & media backup/restore commands.
- Renamed `mediabackup` option (`--no-compress` replaced by explicit `--compress`).

### Removed

- Legacy `DBCommand` code in favor of new connector system.

## [2.5.0] - 2016-03-29

### Added

- `--filename` and `--path` options for `dbbackup` / `dbrestore` commands.
- Binary size unit prefixes in output.

### Changed

- Dropbox storage updated to OAuth2 & Python 3 compatibility.

### Removed

- `DBBACKUP_DROPBOX_ACCESS_TYPE` setting (deprecated by OAuth2 changes).

### Fixed

- NameError for missing `warnings` import.
- Wildcard handling in generated filenames; proper server name derivation for SQLite paths.

## [2.3.3] - 2015-10-05

### Changed

- Initial copy from BitBucket to GitHub.

### Fixed

- Miscellaneous maintenance and minor bug fixes.

[Unreleased]: https://github.com/Archmonger/django-dbbackup/compare/4.3.0...HEAD
[4.3.0]: https://github.com/Archmonger/django-dbbackup/compare/4.2.1...4.3.0
[4.2.1]: https://github.com/Archmonger/django-dbbackup/compare/4.2.0...4.2.1
[4.2.0]: https://github.com/Archmonger/django-dbbackup/compare/4.1.0...4.2.0
[4.1.0]: https://github.com/Archmonger/django-dbbackup/compare/4.0.2...4.1.0
[4.0.2]: https://github.com/Archmonger/django-dbbackup/compare/4.0.1...4.0.2
[4.0.1]: https://github.com/Archmonger/django-dbbackup/compare/4.0.0b0...4.0.1
[4.0.0b0]: https://github.com/Archmonger/django-dbbackup/compare/3.3.0...4.0.0b0
[3.3.0]: https://github.com/Archmonger/django-dbbackup/compare/3.2.0...3.3.0
[3.2.0]: https://github.com/Archmonger/django-dbbackup/compare/3.1.3...3.2.0
[3.1.3]: https://github.com/Archmonger/django-dbbackup/compare/3.1.2...3.1.3
[3.1.2]: https://github.com/Archmonger/django-dbbackup/compare/3.1.1...3.1.2
[3.1.1]: https://github.com/Archmonger/django-dbbackup/compare/3.1.0...3.1.1
[3.1.0]: https://github.com/Archmonger/django-dbbackup/compare/3.0.4...3.1.0
[3.0.4]: https://github.com/Archmonger/django-dbbackup/compare/3.0.3...3.0.4
[3.0.3]: https://github.com/Archmonger/django-dbbackup/compare/3.0.2...3.0.3
[3.0.2]: https://github.com/Archmonger/django-dbbackup/compare/3.0.1...3.0.2
[3.0.1]: https://github.com/Archmonger/django-dbbackup/compare/2.5.0...3.0.1
[2.5.0]: https://github.com/Archmonger/django-dbbackup/compare/2.3.3...2.5.0
[2.3.3]: https://github.com/Archmonger/django-dbbackup/releases/tag/2.3.3
