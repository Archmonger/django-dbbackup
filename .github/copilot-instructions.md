# Django Database Backup Package

Django-dbbackup is a Django application that provides management commands to help backup and restore your project database and media files with various storages such as Amazon S3, Dropbox, local file storage or any Django storage.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

**IMPORTANT**: This package uses modern Python tooling via Hatch (with uv installer). Always use Hatch commands for every development workflow (tests, linting, docs, functional runs, releases).

**BUG INVESTIGATION**: When investigating whether a bug was already resolved in a previous version, always prioritize searching through `CHANGELOG.md` first before using Git history. Only search through Git history when no relevant changelog entries are found.

## Working Effectively

Bootstrap, build, and test the repository:

- `python -m pip install --upgrade pip hatch uv` – install modern Python tooling (≈30s)
- `hatch test` – full unit test matrix (≈30s) **NEVER CANCEL. All tests must pass - failures are never expected or allowed.**
- `hatch run functional:all` – end-to-end functional (SQLite + PostgreSQL live scripts) (≈10–15s) **NEVER CANCEL.**
  - `hatch run functional:sqlite --all` – only SQLite functional cycle
  - `hatch run functional:postgres --all` – only PostgreSQL functional cycle
- `hatch run lint:check` – lint (ruff + pylint) (≈5s)
- `hatch run docs:build` – build documentation (≈2s, strict)
- `hatch run docs:serve` – local docs server (http://localhost:8000)
- `hatch run docs:linkcheck` – validate internal/external links & spelling

**Interactive Development Shell:**

- `hatch shell [ENV_NAME]` - Enter an interactive shell environment with all dependencies installed. ENV_NAME is optional and defaults to the main environment. Use `hatch shell functional` for the functional test environment, `hatch shell lint` for the linting environment, etc.

Build documentation:

- `hatch run docs:build` - builds HTML documentation with MkDocs Material. Takes ~2 seconds. NEVER CANCEL.
- `hatch run docs:serve` - serves documentation locally on http://localhost:8000 for development

## Testing and Validation

Run tests in multiple configurations:

- `hatch test` – unit test runner for all matrix environments
- `hatch test --python 3.12` – isolate matrix to Python 3.12 set
- `hatch run functional:all -v` – functional backup/restore (SQLite + PostgreSQL)
- `hatch run functional:sqlite --all -v` – functional (SQLite only)
- `hatch run functional:postgres --all -v` – functional (PostgreSQL only)
- `hatch run lint:check` – linting
- `hatch run lint:format` – auto-format (Ruff)

Expected test results:

- Unit tests: >200 tests, completes in ~30 seconds across all environments **All tests must always pass - failures are never expected or allowed.**
- Functional tests: database + media backup/restore cycles (SQLite & PostgreSQL), completes in ~10–15 seconds
- Unit tests use an in-repo temporary SQLite database by default

## Manual Validation Scenarios

Always test backup and restore functionality after making changes using functional test environment:

1. **Automated Functional Test (all backends):**

   ```bash
   hatch run functional:all
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

4. **Single Backend Functional Runs (if triaging):**
   ```bash
   hatch run functional:sqlite --all
   hatch run functional:postgres --all
   ```

## Troubleshooting Known Issues

- **Network Timeouts**: Package installations may timeout due to network connectivity. Retry commands if needed.
- **Memory Database Issues**: If you see "no such table" errors, ensure you run migrations first in the appropriate environment
- **Linting Temporarily Disabled**: CI linting checks are temporarily set to pass (marked with `|| true`) pending resolution in future PR
- **Environment Isolation**: Each hatch environment is isolated - dependencies are automatically managed per environment

## Development Workflow

Modern development process using Hatch:

1. **Bootstrap environment**: `pip install --upgrade pip hatch uv`
2. **Make your changes** to the codebase
3. **Run unit tests**: `hatch test` (≈30s) **All must pass - failures are never expected or allowed.**
4. **Run functional tests**: `hatch run functional:all -v` (≈10–15s)
5. **Run linting**: `hatch run lint:check` (5 seconds)
6. **Auto-format code**: `hatch run lint:format` (2 seconds)
7. **Test documentation**: `hatch run docs:build` (2 seconds)
8. **Update documentation** when making changes to Python source code (required)
9. **Add changelog entry** for all significant changes (bug fixes, new features, breaking changes) to `CHANGELOG.md` under the "Unreleased" section.
10. **Lint the changelog** by running `python scripts/validate_changelog.py` (or inside any hatch shell) to ensure format correctness

Always run `hatch run lint:check` before committing. The CI (.github/workflows/build.yml) includes comprehensive checks across all supported Python/Django combinations.

**IMPORTANT**: Documentation must be updated whenever changes are made to Python source code. This is enforced as part of the development workflow.

**IMPORTANT**: Significant changes must always include a changelog entry in `CHANGELOG.md` under the appropriate category (Added, Changed, Deprecated, Removed, Fixed, Security) in the "Unreleased" section.

**IMPORTANT**: Do not add a changelog entry for non-significant changes such as: documentation updates, formatting changes, CI modifications, linting adjustments, new or modified tests, or other non-functional changes.

## Repository Structure and Navigation

Key directories and files:

- `dbbackup/` – main package code
  - `db/` – connector implementations (SQLite, PostgreSQL, MySQL, MongoDB base, etc.)
  - `management/commands/` – Django management commands (dbbackup, dbrestore, mediabackup, mediarestore, listbackups)
  - Core modules: `storage.py`, `settings.py`, `log.py`, `signals.py`, `utils.py`
- `tests/` – comprehensive test suite (unit + helpers)
- `scripts/` – live functional test scripts (`sqlite_live_test.py`, `postgres_live_test.py`)
- `docs/` – MkDocs Material source (built site output under `docs/site/` when building locally)
- `pyproject.toml` – project + Hatch environment configuration
- `.github/workflows/ci.yml` – CI matrix & publish pipeline
- `CHANGELOG.md` – human-maintained change log (search here first for bug history)
- `README.md`, `LICENSE.md`
- `.pre-commit-config.yaml` – git hooks setup

Key configuration files:

- `pyproject.toml` – all tool configuration (Hatch, Ruff, PyLint, PyTest, Coverage)
- `.pre-commit-config.yaml` – git pre-commit hooks
- `tests/settings.py` – Django test settings (locmem email backend)

## Common Hatch Commands

The following are key commands for daily development:

### Development Commands

```bash
hatch test                           # Run all tests across matrix
hatch test --python 3.12             # Test specific Python version subset
hatch run functional:all             # Functional tests (SQLite + PostgreSQL)
hatch run functional:sqlite --all    # Functional tests (SQLite only)
hatch run functional:postgres --all  # Functional tests (PostgreSQL only)
hatch run lint:check                 # Lint (ruff + pylint)
hatch run lint:format                # Auto-format
hatch run lint:format-check          # Format check only
hatch run docs:build                 # Build documentation (strict)
hatch run docs:serve                 # Serve docs locally
hatch run precommit:check            # Run all pre-commit hooks
hatch run precommit:update           # Update hook versions
hatch build                          # Build distribution packages
```

### Environment Management

```bash
hatch env show                       # Show all environments
hatch shell                          # Default dev shell
hatch shell functional               # Functional env shell
hatch shell lint                     # Lint env shell
hatch run --env lint ruff --version  # Run command in lint env
hatch python install 3.13            # (Optional) Install Python 3.13 via Hatch
```

## Hatch Environment Structure

Modern isolated environments configured in pyproject.toml:

### Testing Environments

- **hatch-test**: Unit testing (Python 3.9–3.13 × Django 4.2/5.0/5.1/5.2 matrix)
- **functional**: End-to-end backup/restore (filesystem storage; live SQLite & PostgreSQL scripts)

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

- `DJANGO_SETTINGS_MODULE` – Django settings (default: tests.settings)
- `DB_ENGINE` – database engine (default: django.db.backends.sqlite3)
- `DB_NAME` – database name (default: :memory: for unit tests, tmp/test_db.sqlite3 for functional)
- `STORAGE` – storage backend (default: tests.utils.FakeStorage for unit tests, FileSystemStorage for functional)
- `STORAGE_LOCATION` – filesystem storage path for backups (`tmp/backups/` in functional env)
- `STORAGE_OPTIONS` – extra storage options (`location=tmp/backups/`)
- `MEDIA_ROOT` – media files location (default: tmp/media/)

## Package Dependencies

Modern dependency management via pyproject.toml:

Core runtime dependency:

- django>=4.2

Development dependencies (managed by hatch):

- **Testing**: coverage, django-storages, psycopg2-binary, python-gnupg, testfixtures, python-dotenv
- **Linting**: ruff, pylint
- **Documentation**: mkdocs, mkdocs-material, mkdocs-git-revision-date-localized-plugin, mkdocs-include-markdown-plugin, mkdocs-spellcheck[all], mkdocs-git-authors-plugin, mkdocs-minify-plugin, mike, linkcheckmd
- **Pre-commit**: pre-commit

## CI/CD Pipeline

Modern GitHub Actions workflow (.github/workflows/build.yml):

- **Lint Python**: Code quality checks (temporarily set to pass)
- **Test Python**: Matrix testing across Python 3.9-3.13 with coverage
- **Functional Tests**: End-to-end backup/restore verification (SQLite + PostgreSQL live scripts)
- **Coverage**: Artifact-based coverage combining with 80% threshold
- **Build**: Package building with hatch
- **Publish GitHub**: Automated GitHub release creation on tags
- **Publish PyPI**: Trusted publishing to PyPI on release

## Important Notes

- **This is a Django package**, not a standalone application - it provides management commands for Django projects
- **Backup/restore functionality** works with all Django-compatible databases and various storage backends
- **All builds and tests run quickly** - if something takes more than 60 seconds, investigate network connectivity
- **Hatch environments provide full isolation** - no need to manage virtual environments manually
- **The functional test environment (functional) is the gold standard** - performs real backup/restore cycles (SQLite + PostgreSQL)
- **Documentation updates are required** when making changes to Python source code
- **Always update this file** when making changes to the development workflow, build process, or repository structure
- **Tests use a repository-local tmp/ directory** instead of system /tmp for portability (especially on Windows) and cleaner CI artifacts.
