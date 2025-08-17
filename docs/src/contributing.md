# Contributing guide

Django-dbbackup is a free license software where all help is welcomed. This
documentation aims to help users or developers to bring their contributions
to this project.

## Creating a development environment

If you plan to make code changes to this repository, you will need to install the following dependencies first:

-   [Git](https://git-scm.com/downloads)
-   [Python 3.9+](https://www.python.org/downloads/)
-   [Hatch](https://hatch.pypa.io/latest/)

Once you finish installing these dependencies, you can clone this repository:

```shell
git clone https://github.com/Archmonger/django-dbbackup.git
cd django-dbbackup
```

## Executing test environment commands

By utilizing `hatch`, the following commands are available to manage the development environment.

### Tests

| Command | Description |
| --- | --- |
| `hatch test` | Run Python tests using the current environment's Python version |
| `hatch test --all` | Run tests using all compatible Python and Django versions |
| `hatch test --python 3.9` | Run tests using a specific Python version |
| `hatch test --include "django=5.1"` | Run tests using a specific Django version |
| `hatch test -k test_backup_filter` | Run only a specific test |

??? question "What other arguments are available to me?"

    The `hatch test` command is a wrapper for `pytest`. Hatch "intercepts" a handful of arguments, which can be previewed by typing `hatch test --help`.

    Any additional arguments in the `test` command are directly passed on to pytest. See the [pytest documentation](https://docs.pytest.org/en/stable/reference/reference.html#command-line-flags) for what additional arguments are available.

### Linting and Formatting

| Command | Description |
| --- | --- |
| `hatch run lint:format` | Run formatters to fix code style |
| `hatch run lint:format-check` | Check code formatting without making changes |
| `hatch run lint:check` | Run all linters |
| `hatch run precommit:check` | Run all [`pre-commit`](https://pre-commit.com/) checks configured within this repository |
| `hatch run precommit:update` | Update the [`pre-commit`](https://pre-commit.com/) hooks configured within this repository |

??? tip "Configure your IDE for linting"

    This repository uses `ruff` and `pylint` for linting and formatting.

    You can install `ruff` as a plugin to your preferred code editor to create a similar environment.

### Functional Testing

| Command | Description |
| --- | --- |
| `hatch run functional:test` | Run end-to-end backup and restore tests |

The functional tests perform real database and media backup/restore cycles to ensure the commands work correctly.

### Documentation

| Command | Description |
| --- | --- |
| `hatch run docs:serve` | Start the [`mkdocs`](https://www.mkdocs.org/) server to view documentation locally |
| `hatch run docs:build` | Build the documentation |

### Environment Management

| Command | Description |
| --- | --- |
| `hatch build --clean` | Build the package from source |
| `hatch env prune` | Delete all virtual environments created by `hatch` |
| `hatch python install 3.12` | Install a specific Python version to your system |

??? tip "Check out Hatch for all available commands!"

    This documentation only covers commonly used commands.

    You can type `hatch --help` to see all available commands.

## Submit a bug, issue or enhancement

All communication are made with [GitHub issues](https://github.com/Archmonger/django-dbbackup/issues). Do not hesitate to open a
issue if:

- You have an improvement idea
- You found a bug
- You've got a question
- More generally something seems wrong for you

## Make a patch

We use [GitHub pull requests](https://github.com/Archmonger/django-dbbackup/pulls) to manage all patches. For a better handling
of requests we advise you to:

1. Fork the project and make a new branch
2. Make your changes with tests if possible and documentation if needed
3. Run `hatch test` and `hatch run functional:test` to verify your changes
4. Run `hatch run lint:check` to ensure code quality
5. Push changes to your fork repository and test it with GitHub Actions
6. If it succeeds, open a pull request
7. Bother us until we give you an answer

!!! note
    We recommend testing with multiple Python and Django versions using
    `hatch test --all` before pushing. DBBackup uses a lot of file operations,
    so breaks between versions are possible.

## Test environment configuration

DBBackup contains a test Django project at `dbbackup.tests` and its
`settings` module. This configuration takes care of the following
environment variables:

**`DB_ENGINE`** - Default: `django.db.backends.sqlite3`

Database engine to use. See `django.db.backends` for default backends.

**`DB_NAME`** - Default: `:memory:`

Database name. Should be set correctly if a database other than sqlite3 is used.

**`DB_USER`** - Default: `None`

Database username

**`DB_PASSWORD`** - Default: `None`

Database password

**`DB_HOST`** - Default: `None`

Database host

**`MEDIA_ROOT`** - Default= `tempfile.mkdtemp()`

Django's `MEDIA_ROOT`, useful if you want test media backup from filesystem

**`STORAGE`** - Default: `dbbackup.tests.utils.FakeStorage`

Storage used for backups

**`STORAGE_OPTIONS`**

Options for instantiating the chosen storage. It must be formatted as
`"key1=foo,key2=bar"` and will be converted into a `dict`.
