# Django Database Backup Package

Django-dbbackup is a Django application that provides management commands to help backup and restore your project database and media files with various storages such as Amazon S3, Dropbox, local file storage or any Django storage.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

Bootstrap, build, and test the repository:
- `python -m pip install --upgrade pip`
- `pip install -r requirements.txt` - installs core Django dependencies (takes ~30 seconds)
- `pip install -r requirements/tests.txt` - installs testing dependencies including coverage, flake8, pylint, tox (takes ~60 seconds)
- `python runtests.py` - runs unit test suite. Takes ~3 seconds. NEVER CANCEL.
- `bash functional.sh` - runs end-to-end functional tests for backup/restore workflows. Takes ~2 seconds. NEVER CANCEL.
- `flake8 dbbackup` - runs linting on the main package. Takes ~1 second. NEVER CANCEL.

Build documentation:
- `pip install -r requirements/docs.txt` - install documentation dependencies (takes ~30 seconds, may timeout due to network issues)
- `make docs` - builds HTML documentation with Sphinx. Takes ~1 second. NEVER CANCEL.

## Testing and Validation

Run tests in multiple configurations:
- `python runtests.py` - unit test launcher (3 seconds)
- `bash functional.sh` - uses `runtests.py` to run backup/restore test in the current environment (2 seconds)
- `tox -e py312-django42` - run tests in a specific isolated environment (may timeout due to network issues, set timeout to 20+ seconds)
- `flake8 dbbackup` - linting on main package (1 second)

Expected test results:
- Unit tests: >200 tests, completes in ~3 seconds
- Functional tests: database and media backup/restore cycles, completes in ~2 seconds
- All tests use SQLite in-memory database by default

## Manual Validation Scenarios

Always test backup and restore functionality after making changes:

1. **Database Backup/Restore Test:**
   ```bash
   python runtests.py migrate --noinput
   python runtests.py dbbackup --noinput
   python runtests.py listbackups
   python runtests.py dbrestore --noinput
   ```

2. **Media Backup/Restore Test:**
   ```bash
   mkdir -p /tmp/media
   echo "test file" > /tmp/media/test.txt
   MEDIA_ROOT=/tmp/media python runtests.py mediabackup
   rm /tmp/media/test.txt
   MEDIA_ROOT=/tmp/media python runtests.py mediarestore --noinput
   ls /tmp/media/  # should show restored test.txt
   ```

3. **Management Commands Test:**
   ```bash
   python runtests.py help dbbackup
   python runtests.py help dbrestore
   python runtests.py help mediabackup
   python runtests.py help mediarestore
   python runtests.py help listbackups
   ```

## Troubleshooting Known Issues

- **Tox Network Timeouts**: `tox` commands may fail with "Read timed out" errors due to network connectivity. This is environmental, not code-related.
- **Pip Installation Timeouts**: `pip install` commands may timeout when installing documentation dependencies. Dependencies are likely already installed from previous steps.
- **SQLite Restore Warnings**: Warnings about "UNIQUE constraint failed" during restore operations are normal for test scenarios
- **Memory Database Issues**: If you see "no such table" errors, ensure you run `python runtests.py migrate --noinput` first
- **Manual Backup/Restore Limitations**: Some manual backup/restore commands may fail with "There's no backup file available" when using test storage backend. Use `bash functional.sh` for complete end-to-end testing.
- **Flake8 Scanning Wrong Directories**: Run `flake8 dbbackup` to lint only the main package, not `flake8` alone which scans unnecessary directories like `.tox/`

## Development Workflow

Standard development process:
1. **Always run the bootstrapping steps first** (install dependencies)
2. **Make your changes** to the codebase
3. **Run unit tests**: `python runtests.py` (3 seconds)
4. **Run functional tests**: `bash functional.sh` (2 seconds)  
5. **Run linting**: `flake8` (1 second)
6. **Test manually** with backup/restore scenarios above
7. **Build docs if needed**: `make docs` (2 seconds)

Always run `flake8 dbbackup` before committing or the CI (.github/workflows/build.yml) will fail.

## Repository Structure and Navigation

Key directories and files:
- `dbbackup/` - main package code
  - `management/commands/` - Django management commands (dbbackup, dbrestore, etc.)
  - `db/` - database connector implementations (MySQL, PostgreSQL, SQLite, etc.)  
  - `storage.py` - storage backend interface
  - `tests/` - comprehensive test suite
- `docs/` - Sphinx documentation source
- `requirements/` - split requirement files (tests.txt, docs.txt, build.txt, dev.txt)
- `runtests.py` - test runner, acts like Django's manage.py for testing
- `functional.sh` - end-to-end test script for backup/restore workflows
- `Makefile` - build automation (test, docs, clean targets)
- `tox.ini` - multi-environment testing configuration
- `.github/workflows/build.yml` - CI/CD pipeline
- `setup.py` - package definition and dependencies

Key configuration files:
- `pyproject.toml` - black and isort configuration
- `.pre-commit-config.yaml` - git pre-commit hooks setup
- `.flake8` configuration in `tox.ini`
- `dbbackup/tests/settings.py` - Django test settings

## Common Tasks

The following are outputs from frequently run commands. Reference them instead of viewing, searching, or running bash commands to save time.

### Repository Root Structure
```
ls -la
.coveragerc          .pre-commit-config.yaml  codecov.yml        pyproject.toml
.env-example         .pylintrc                dbbackup/          requirements/
.git/                .readthedocs.yaml        docs/              requirements.txt
.github/             .sourcery.yaml           functional.sh      runtests.py
.gitignore           .vscode/                 LICENSE.txt        setup.py
.yamllint.yaml       AUTHORS.txt              MANIFEST.in        tox.ini
                     CHANGELOG.rst            Makefile
```

### Main Package Structure
```
ls dbbackup/
VERSION          apps.py          log.py           storage.py
__init__.py      checks.py        management/      tests/
__pycache__/     db/              settings.py      utils.py
```

### Available Management Commands
```
python runtests.py help

[dbbackup]
    dbbackup      - Backup a database, encrypt and/or compress
    dbrestore     - Restore a database backup
    listbackups   - List available backup files  
    mediabackup   - Backup media files
    mediarestore  - Restore media files backup
```

### Test Configuration
- Default database: SQLite in-memory (`:memory:`)
- Test runner: `runtests.py` (equivalent to `manage.py` for testing)
- Settings: `dbbackup.tests.settings`
- Test data models: `dbbackup.tests.testapp.models`

### Build Timing Expectations
- **NEVER CANCEL**: All commands complete within 5 minutes
- Dependency installation: 1-30 seconds (may timeout due to network)
- Unit tests: 1 second (set timeout to 30+ seconds)
- Functional tests: 2 seconds (set timeout to 30+ seconds)
- Linting: 0.2 seconds (set timeout to 30+ seconds)
- Documentation build: 1 second (set timeout to 30+ seconds)
- Tox environments: 5+ minutes (set timeout to 600+ seconds, may fail due to network)

### Environment Variables for Testing
- `DB_ENGINE` - database engine (default: django.db.backends.sqlite3)
- `DB_NAME` - database name (default: :memory:)
- `STORAGE` - storage backend (default: dbbackup.tests.utils.FakeStorage)
- `MEDIA_ROOT` - media files location (default: tempfile.mkdtemp())
- `DJANGO_SETTINGS_MODULE` - Django settings (default: dbbackup.tests.settings)

## Package Dependencies

Core runtime dependencies (requirements.txt):
- django>=4.2
- pytz

Test dependencies (requirements/tests.txt):
- coverage, flake8, pylint (code quality)
- python-gnupg>=0.5.0 (encryption support)
- psycopg2-binary (PostgreSQL testing)
- django-storages (cloud storage testing)
- tox, tox-gh-actions (multi-environment testing)

Documentation dependencies (requirements/docs.txt):
- sphinx, sphinx-rtd-theme
- sphinx-django-command (Django command documentation)

## Important Notes

- **This is a Django package**, not a standalone application - it provides management commands for Django projects
- **Backup/restore functionality** works with SQLite, MySQL, PostgreSQL databases and various storage backends
- **All builds and tests run very quickly** - if something takes more than 5 minutes, investigate network connectivity
- **The functional.sh script is the gold standard** for testing - it performs real backup and restore operations
