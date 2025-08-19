# Database settings

The following databases are supported by this application:

- SQLite
- MySQL
- PostgreSQL
- MongoDB
- ...and any other that you might implement

By default DBBackup reuses connection details from `settings.DATABASES`.
Sometimes you want different credentials or a different host (e.g. read-only
replica) just for backups. Use `DBBACKUP_CONNECTORS` for that purpose; it
mirrors Django's `DATABASES` structure but only overrides the keys you supply.

```python
DBBACKUP_CONNECTORS = {
    'default': {
        'USER': 'backupuser',
        'PASSWORD': 'backuppassword',
        'HOST': 'replica-for-backup'
    }
}
```

This configuration will allow you to use a replica with a different host and user,
which is a great practice if you don't want to overload your main database.

DBBackup uses “connector” classes to implement backend specific dump and
restore logic. Each connector may expose additional settings documented
below.

## Common

All connectors have the following parameters:

### CONNECTOR

Absolute path to a connector class by default is:

- `dbbackup.db.sqlite.SqliteConnector` for `'django.db.backends.sqlite3'`
- `dbbackup.db.mysql.MysqlDumpConnector` for `django.db.backends.mysql`
- `dbbackup.db.postgresql.PgDumpConnector` for `django.db.backends.postgresql`
- `dbbackup.db.postgresql.PgDumpGisConnector` for `django.contrib.gis.db.backends.postgis`
- `dbbackup.db.mongodb.MongoDumpConnector` for `django_mongodb_engine`

All supported built-in connectors are described in more detail below.

Following database wrappers from `django-prometheus` module are supported:

- `django_prometheus.db.backends.postgresql` for `dbbackup.db.postgresql.PgDumpBinaryConnector`
- `django_prometheus.db.backends.sqlite3` for `dbbackup.db.sqlite.SqliteConnector`
- `django_prometheus.db.backends.mysql` for `dbbackup.db.mysql.MysqlDumpConnector`
- `django_prometheus.db.backends.postgis` for `dbbackup.db.postgresql.PgDumpGisConnector`

### EXCLUDE

List of table names to exclude from the dump. Not all connectors support this
when using snapshot/copy approaches (e.g. raw file copy). Example:

```python
DBBACKUP_CONNECTORS = {
    'default': {
        'EXCLUDE': ['django_session', 'temp_data'],
    }
}
```

### EXTENSION

File extension used for the generated dump archive. Default `'dump'`.

## Command connectors

Some connectors use a command line tool as a dump engine, `mysqldump` for
example. These kinds of tools have common attributes:

### DUMP_CMD

Path to the command used to create a backup; default is the appropriate
command supposed to be in your PATH, for example: `'mysqldump'` for MySQL.

This setting is useful only for connectors using command line tools (children
of `dbbackup.db.base.BaseCommandDBConnector`)

### RESTORE_CMD

Same as `DUMP_CMD` but used when restoring.

### DUMP_PREFIX and RESTORE_PREFIX

String to include as prefix of dump or restore command. It will be added with
a space between the launched command and its prefix.

### DUMP_SUFFIX and RESTORE_SUFFIX

String to include as suffix of dump or restore command. It will be added with
a space between the launched command and its suffix.

### ENV, DUMP_ENV and RESTORE_ENV

Environment variables injected when running the external dump/restore
commands. `ENV` applies to every command; `DUMP_ENV` / `RESTORE_ENV` override
or extend it for their respective phases. Defaults: all `{}`.

Example forcing a specific SSL mode for PostgreSQL dump:

```python
DBBACKUP_CONNECTORS = {
    'default': {
        'DUMP_ENV': {'PGSSLMODE': 'require'}
    }
}
```

### USE_PARENT_ENV

Specify if the connector will use its parent's environment variables. By
default it is `True` to keep `PATH`.

## SQLite

SQLite defaults to `dbbackup.db.sqlite.SqliteConnector`.

### SqliteConnector

It is in pure Python and is similar to the Sqlite `.dump` command for creating a
SQL dump.

### SqliteBackupConnector

The `dbbackup.db.sqlite.SqliteBackupConnector` makes a copy of the SQLite database file using the `.backup` command, which is safe to execute while the database has ongoing/active connections. Additionally, it supports dumping in-memory databases by construction.

### SqliteCPConnector

You can also use `dbbackup.db.sqlite.SqliteCPConnector` for making a
simple raw copy of your database file, like a snapshot.

In-memory databases aren't dumpable with it.

## MySQL

MySQL defaults to `dbbackup.db.mysql.MysqlDumpConnector` which shells out to
`mysqldump` for creation and `mysql` for restore.

## PostgreSQL

PostgreSQL uses by default `dbbackup.db.postgresql.PgDumpConnector`, but
we advise you to use `dbbackup.db.postgresql.PgDumpBinaryConnector`. The
first one uses `pg_dump` and `psql` for its job, creating RAW SQL files.

The second uses `pg_restore` with binary dump files for faster, parallel-
capable restores.

Both may invoke `psql` for ancillary administrative statements.

### SINGLE_TRANSACTION

When doing a restore, wrap everything in a single transaction so errors
cause a rollback.

This corresponds to `--single-transaction` argument of `psql` and
`pg_restore`.

Default: `True`

### DROP

With `PgDumpConnector`, it includes table-dropping statements in the dump file.
`PgDumpBinaryConnector` drops during restore.

This corresponds to `--clean` argument of `pg_dump` and `pg_restore`.

Default: `True`

### IF_EXISTS

Adds `IF EXISTS` to destructive statements in `--clean` mode of `pg_dump`.

Default: `False`

## PostGIS

Set in `dbbackup.db.postgresql.PgDumpGisConnector`, it does the same as
PostgreSQL but launches `CREATE EXTENSION IF NOT EXISTS postgis;` before
restoring the database.

### PSQL_CMD

Path to the `psql` command used for administration tasks like enabling PostGIS;
default is `psql`.

### PASSWORD

If you fill this setting the `PGPASSWORD` environment variable will be used
with every command. For security reasons, we advise using a `.pgpass` file.

### ADMIN_USER

Username used to launch actions requiring privileges, such as extension creation.

### ADMIN_PASSWORD

Password used to launch actions requiring privileges, such as extension creation.

### SCHEMAS

Limit the dump to specific schemas (PostgreSQL connectors only). If omitted,
all non system schemas are included. Provide a list of schema names.

## MongoDB

MongoDB uses by default `dbbackup.db.mongodb.MongoDumpConnector`. It
uses `mongodump` and `mongorestore` for its job.

For authentication enabled MongoDB deployments add the `AUTH_SOURCE` option to
indicate the database used to verify credentials.

```python
DBBACKUP_CONNECTORS = {
    'default': {
        ...
        'AUTH_SOURCE': 'admin',
    }
}
```

Or in `DATABASES` one:

```python
DATABASES = {
    'default': {
        ...
        'AUTH_SOURCE': 'admin',
    }
}
```

### OBJECT_CHECK

Validate documents before inserting into the database (option `--objcheck` on the command line); default is `True`.

### DROP

Replace objects that are already in the database (option `--drop` on the command line); default is `True`.

## Custom connectors

To implement a custom connector, subclass `dbbackup.db.base.BaseDBConnector`
and implement `_create_dump` / `_restore_dump`. If you need to run external
commands, subclass `dbbackup.db.base.BaseCommandDBConnector` to inherit
argument assembly helpers and environment handling.

Here is an example, on how to easily use a custom connector that you have created or even that you simply want to reuse:

```python
DBBACKUP_CONNECTOR_MAPPING = {
    'transaction_hooks.backends.postgis': 'dbbackup.db.postgresql.PgDumpGisConnector',
}
```

Swap in any custom connector path you created. The left hand side engine name
should match the `ENGINE` value Django reports for that database alias.
