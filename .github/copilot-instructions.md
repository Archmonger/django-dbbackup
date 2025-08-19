# Django Database Backup Package

Django-dbbackup is a Django application that provides management commands to help backup and restore your project database and media files with various storages such as Amazon S3, Dropbox, local file storage or any Django storage.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

**IMPORTANT**: This package has been fully migrated to modern Python tooling using Hatch. Always use Hatch commands for development workflows.

**BUG INVESTIGATION**: When investigating whether a bug was already resolved in a previous version, always prioritize searching through `CHANGELOG.md` first before using Git history. Only search through Git history when no relevant changelog entries are found.

## Working Effectively

Bootstrap, build, and test the repository:

- `python -m pip install --upgrade pip hatch uv` - installs modern Python tooling (takes ~30 seconds)
- `hatch test` - runs comprehensive unit test suite across all Python/Django versions. Takes ~30 seconds. NEVER CANCEL. **All tests must always pass - failures are never expected or allowed.**
- `hatch run functional:test` - runs end-to-end functional tests for backup/restore workflows. Takes ~10 seconds. NEVER CANCEL.
- `hatch run lint:check` - runs linting on the main package. Takes ~5 seconds. NEVER CANCEL.
- `hatch run lint:format-check` - runs code formatting checks. Takes ~2 seconds. NEVER CANCEL.

**Interactive Development Shell:**

- `hatch shell [ENV_NAME]` - Enter an interactive shell environment with all dependencies installed. ENV_NAME is optional and defaults to the main environment. Use `hatch shell functional` for the functional test environment, `hatch shell lint` for the linting environment, etc.

Build documentation:

- `hatch run docs:build` - builds HTML documentation with MkDocs Material. Takes ~2 seconds. NEVER CANCEL.
- `hatch run docs:serve` - serves documentation locally on http://localhost:8000 for development

## Testing and Validation

Run tests in multiple configurations:

- `hatch test` - unit test runner for all environments (30 seconds) **All tests must always pass - failures are never expected or allowed.**
- `hatch test --python 3.12` - test on specific Python version (10 seconds)
- `hatch run functional:test` - complete backup/restore test cycle in real filesystem environment (10 seconds)
- `hatch run lint:check` - linting on main package (5 seconds)
- `hatch run lint:format` - auto-format code using Ruff (2 seconds)

Expected test results:

- Unit tests: >200 tests, completes in ~30 seconds across all environments **All tests must always pass - failures are never expected or allowed.**
- Functional tests: database and media backup/restore cycles, completes in ~10 seconds
- All tests use a SQLite filesystem database by default

## Manual Validation Scenarios

Always test backup and restore functionality after making changes using functional test environment:

1. **Database Backup/Restore Test:**

   ```bash
   hatch run functional:test  # Comprehensive automated test
   ```

2. **Manual Database Test (if needed):**

   ```bash
   hatch shell functional
   python -m django migrate --noinput
   python -m django dbbackup --noinput
   python -m django listbackups
   python -m django dbrestore --noinput
   ```

3. **Manual Media Test (if needed):**
   ```bash
   hatch shell functional
   mkdir -p tmp/media
   echo "test file" > tmp/media/test.txt
   python -m django mediabackup --noinput
   rm tmp/media/test.txt
   python -m django mediarestore --noinput
   ls tmp/media/  # should show restored test.txt
   ```

## Troubleshooting Known Issues

- **Network Timeouts**: Package installations may timeout due to network connectivity. Retry commands if needed.
- **SQLite Restore Warnings**: Warnings about "UNIQUE constraint failed" during restore operations are normal for test scenarios
- **Memory Database Issues**: If you see "no such table" errors, ensure you run migrations first in the appropriate environment
- **Linting Temporarily Disabled**: CI linting checks are temporarily set to pass (marked with `|| true`) pending resolution in future PR
- **Environment Isolation**: Each hatch environment is isolated - dependencies are automatically managed per environment

## Development Workflow

Modern development process using Hatch:

1. **Bootstrap environment**: `pip install --upgrade pip hatch uv`
2. **Make your changes** to the codebase
3. **Run unit tests**: `hatch test` (30 seconds) **All tests must always pass - failures are never expected or allowed.**
4. **Run functional tests**: `hatch run functional:test` (10 seconds)
5. **Run linting**: `hatch run lint:check` (5 seconds)
6. **Auto-format code**: `hatch run lint:format` (2 seconds)
7. **Test documentation**: `hatch run docs:build` (2 seconds)
8. **Update documentation** when making changes to Python source code (required)
9. **Add changelog entry** for all significant changes (bug fixes, new features, breaking changes) to `CHANGELOG.md` under the "Unreleased" section.
10. **Lint the changelog** by running `hatch run scripts/validate_changelog.py` to ensure it follows the correct format

Always run `hatch run lint:check` before committing. The CI (.github/workflows/build.yml) includes comprehensive checks across all supported Python/Django combinations.

**IMPORTANT**: Documentation must be updated whenever changes are made to Python source code. This is enforced as part of the development workflow.

**IMPORTANT**: Significant changes must always include a changelog entry in `CHANGELOG.md` under the appropriate category (Added, Changed, Deprecated, Removed, Fixed, Security) in the "Unreleased" section. Do not add entries for minor changes such as documentation updates, formatting changes, CI modifications, linting adjustments, changes to test related code, or other non-functional changes.

## Repository Structure and Navigation

Key directories and files:

- `dbbackup/` - main package code
  - `management/commands/` - Django management commands (dbbackup, dbrestore, etc.)
  - `db/` - database connector implementations (MySQL, PostgreSQL, SQLite, etc.)
  - `storage.py` - storage backend interface
  - `tests/` - comprehensive test suite
- `docs/` - MkDocs Material documentation source
- `pyproject.toml` - modern Python project configuration with Hatch environments
- `.github/workflows/build.yml` - CI/CD pipeline with hatch-based testing and publishing
- `conftest.py` - pytest configuration for Django test setup

Key configuration files:

- `pyproject.toml` - all tool configuration (hatch, ruff, pylint, pytest, coverage)
- `.pre-commit-config.yaml` - git pre-commit hooks setup
- `dbbackup/tests/settings.py` - Django test settings with EMAIL_BACKEND for testing

## Common Hatch Commands

The following are key commands for daily development:

### Development Commands

```bash
hatch test                          # Run all tests across environments
hatch test --python 3.12           # Test specific Python version
hatch run functional:test           # End-to-end backup/restore tests
hatch run lint:check               # Run linting (ruff + pylint)
hatch run lint:format              # Auto-format code
hatch run lint:format-check        # Check formatting without changing
hatch run docs:build               # Build documentation
hatch run docs:serve               # Serve docs locally
hatch build                        # Build distribution packages
```

### Environment Management

```bash
hatch env show                      # Show all environments
hatch shell                         # Enter default shell
hatch shell functional             # Enter functional test shell
hatch run --env lint ruff --version # Run command in specific environment
```

## Hatch Environment Structure

Modern isolated environments configured in pyproject.toml:

### Testing Environments

- **hatch-test**: Unit testing across Python 3.9-3.13 and Django 4.2-5.2 combinations
- **functional**: End-to-end testing with real filesystem storage

### Development Environments

- **lint**: Code quality (ruff, pylint)
- **docs**: Documentation building (mkdocs-material)
- **precommit**: Git hooks management

### Test Configuration

- Default database: SQLite file-based (`tmp/test_db.sqlite3` within the repository)
- Email testing: Django locmem backend (`django.core.mail.backends.locmem.EmailBackend`)
- Settings: `dbbackup.tests.settings`
- Test data models: `dbbackup.tests.testapp.models`

### Build Timing Expectations

- **NEVER CANCEL**: All commands complete within 60 seconds
- Dependency installation: 5-30 seconds (hatch manages automatically)
- Unit tests: 10-30 seconds (varies by environment matrix)
- Functional tests: 5-10 seconds
- Linting: 2-5 seconds
- Documentation build: 1-2 seconds

### Environment Variables for Testing

- `DJANGO_SETTINGS_MODULE` - Django settings (default: dbbackup.tests.settings)
- `DB_ENGINE` - database engine (default: django.db.backends.sqlite3)
- `DB_NAME` - database name (default: :memory: for unit tests, tmp/test_db.sqlite3 for functional)
- `STORAGE` - storage backend (default: dbbackup.tests.utils.FakeStorage for unit, FileSystemStorage for functional)
- `MEDIA_ROOT` - media files location (default: tmp/media/)

## Package Dependencies

Modern dependency management via pyproject.toml:

Core runtime dependencies:

- django>=4.2
- pytz

Development dependencies (managed by hatch):

- **Testing**: coverage, django-storages, psycopg2-binary, python-gnupg, testfixtures
- **Linting**: ruff, pylint
- **Documentation**: mkdocs, mkdocs-material
- **Pre-commit**: pre-commit

## CI/CD Pipeline

Modern GitHub Actions workflow (.github/workflows/build.yml):

- **Lint Python**: Code quality checks (temporarily set to pass)
- **Test Python**: Matrix testing across Python 3.9-3.13 with coverage
- **Functional Tests**: End-to-end backup/restore verification
- **Coverage**: Artifact-based coverage combining with 80% threshold
- **Build**: Package building with hatch
- **Publish GitHub**: Automated GitHub release creation on tags
- **Publish PyPI**: Trusted publishing to PyPI on release

## Important Notes

- **This is a Django package**, not a standalone application - it provides management commands for Django projects
- **Backup/restore functionality** works with SQLite, MySQL, PostgreSQL databases and various storage backends
- **All builds and tests run quickly** - if something takes more than 60 seconds, investigate network connectivity
- **Hatch environments provide full isolation** - no need to manage virtual environments manually
- **The functional test environment is the gold standard** - it performs real backup and restore operations with filesystem storage
- **Documentation updates are required** when making changes to Python source code
- **Always update this file** when making changes to the development workflow, build process, or repository structure
- **Tests use a repository-local tmp/ directory** instead of system /tmp for portability (especially on Windows) and cleaner CI artifacts.
