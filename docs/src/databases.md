# Database settings

The following databases are supported by this application:

- SQLite
- MySQL
- PostgreSQL
- MongoDB
- ... and any other Django-supported database (via `DjangoConnector`)

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

## Common Settings

All connectors have the following parameters:

| Setting   | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Default                     |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| CONNECTOR | Absolute path to connector class. Defaults by engine: `dbbackup.db.sqlite.SqliteBackupConnector` (sqlite3), `dbbackup.db.mysql.MysqlDumpConnector` (mysql), `dbbackup.db.postgresql.PgDumpConnector` (postgresql), `dbbackup.db.postgresql.PgDumpGisConnector` (postgis), `dbbackup.db.mongodb.MongoDumpConnector` (django_mongodb_engine), `dbbackup.db.django.DjangoConnector` (fallback / any unmapped). Prometheus wrappers are also supported mapping to the same connectors. | Auto-detected from `ENGINE` |
| EXCLUDE   | List of table names to exclude from dump (may be unsupported for raw file copy snapshot approaches). Example below.                                                                                                                                                                                                                                                                                                                                                          | None                        |
| EXTENSION | File extension used for the generated dump archive.                                                                                                                                                                                                                                                                                                                                                                                                                          | `dump`                      |

All supported built-in connectors are described in more detail below. Following database wrappers from `django-prometheus` are supported: `django_prometheus.db.backends.postgresql` (-> `PgDumpBinaryConnector`), `django_prometheus.db.backends.sqlite3` (-> `SqliteBackupConnector`), `django_prometheus.db.backends.mysql` (-> `MysqlDumpConnector`), `django_prometheus.db.backends.postgis` (-> `PgDumpGisConnector`).

Example for `EXCLUDE` usage:

```python
DBBACKUP_CONNECTORS = {
    'default': {
        'EXCLUDE': ['django_session', 'temp_data'],
    }
}
```

Some connectors use a command line tool as a dump engine, `mysqldump` for
example. These kinds of tools have common attributes:

| Setting                      | Description                                                                                                                                                           | Default                                |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| DUMP_CMD                     | Path to command used to create a backup (e.g. `mysqldump`, `pg_dump`, `mongodump`). Applies only to command-line connectors (subclasses of `BaseCommandDBConnector`). | Tool name inferred / must be in `PATH` |
| RESTORE_CMD                  | Path to command used for restore (e.g. `mysql`, `psql`, `pg_restore`, `mongorestore`).                                                                                | Tool name inferred / must be in `PATH` |
| DUMP_PREFIX / RESTORE_PREFIX | String inserted (with a space) before the actual dump/restore command (e.g. to add `time` or `nice`).                                                                 | None                                   |
| DUMP_SUFFIX / RESTORE_SUFFIX | String appended (with a space) after the dump/restore command (e.g. to pipe or redirect).                                                                             | None                                   |
| ENV                          | Base environment variables applied to every external command.                                                                                                         | `{}`                                   |
| DUMP_ENV / RESTORE_ENV       | Environment overrides/extensions applied only to dump / restore phases.                                                                                               | `{}`                                   |
| USE_PARENT_ENV               | Whether to inherit parent process environment (e.g. to keep `PATH`).                                                                                                  | `True`                                 |

Example forcing a specific SSL mode for PostgreSQL dump:

```python
DBBACKUP_CONNECTORS = {
    'default': {
        'DUMP_ENV': {'PGSSLMODE': 'require'}
    }
}
```

## Built-in Database Connectors

These connectors are provided by default and are designed to work with specific database engines. They provide optimized backup and restore functionality.

### SQLite

#### SqliteBackupConnector

The `dbbackup.db.sqlite.SqliteBackupConnector` makes a copy of the SQLite database file using the `.backup` command, which is safe to execute while the database has ongoing/active connections.

This is the default connector for SQLite databases.

#### SqliteConnector

It is in pure Python and is similar to the Sqlite `.dump` command for creating a SQL dump.

This connector can be used to restore a backup to an existing (dirty) database due to it's generation of raw SQL statements. However, that is generally not recommended and can lead to unexpected results depending on your schema.

#### SqliteCPConnector

The `dbbackup.db.sqlite.SqliteCPConnector` connector can be used to make a simple raw copy of your database file, like a snapshot.

In-memory databases are **not** dumpable with it. Since it works by copying the database file directly, it is not suitable for databases that are have active connections.

### MySQL

MySQL defaults to `dbbackup.db.mysql.MysqlDumpConnector` which shells out to
`mysqldump` for creation and `mysql` for restore.

### PostgreSQL

All PostgreSQL connectors have the following settings:

#### Settings

| Setting            | Description                                                                                                                             | Default |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| SINGLE_TRANSACTION | Wrap restore in a single transaction so errors cause full rollback (`--single-transaction` for `psql` / `pg_restore`).                  | `True`  |
| DROP               | Include / execute drop statements when restoring (`--clean` with `pg_dump` / `pg_restore`). In binary mode drops happen during restore. | `True`  |
| IF_EXISTS          | Add `IF EXISTS` to destructive statements in clean mode. Automatically enabled when `DROP=True` to prevent identity column errors.      | `False` |
| ENABLE_ROW_SECURITY | Enable row-level security for dumping data (`--enable-row-security` with `pg_dump`). Required for databases with row-level security policies. | `False` |

Example configuration for databases with row-level security:

```python
DBBACKUP_CONNECTORS = {
    'default': {
        'ENABLE_ROW_SECURITY': True
    }
}
```

#### PgDumpConnector

The `dbbackup.db.postgresql.PgDumpConnector` uses `pg_dump` to create RAW SQL files and `psql` to restore them.

This is the default connector for PostgreSQL databases, however, it is recommended to use the binary connector for better performance.

#### PgDumpBinaryConnector

The `dbbackup.db.postgresql.PgDumpBinaryConnector` is similar to PgDumpConnector, but it uses `pg_dump` in binary mode and restores using `pg_restore`.

This allows for faster and parallel-capable restores. It may still invoke `psql` for administrative tasks.

### PostGIS

Set in `dbbackup.db.postgresql.PgDumpGisConnector`, it does the same as
PostgreSQL but launches `CREATE EXTENSION IF NOT EXISTS postgis;` before
restoring the database.

#### Settings

| Setting        | Description                                                                     | Default                |
| -------------- | ------------------------------------------------------------------------------- | ---------------------- |
| PSQL_CMD       | Path to `psql` used for admin tasks (extension creation, etc.).                 | `psql`                 |
| PASSWORD       | If provided sets `PGPASSWORD` for all commands (prefer `.pgpass` for security). | None                   |
| ADMIN_USER     | Privileged user for administrative actions like enabling PostGIS.               | None                   |
| ADMIN_PASSWORD | Password for `ADMIN_USER` when needed.                                          | None                   |
| SCHEMAS        | Limit dump to specific schemas (PostgreSQL connectors only).                    | All non-system schemas |

### MongoDB

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

... or in `DATABASES`:

```python
DATABASES = {
    'default': {
        ...
        'AUTH_SOURCE': 'admin',
    }
}
```

#### Settings

| Setting      | Description                                         | Default |
| ------------ | --------------------------------------------------- | ------- |
| OBJECT_CHECK | Validate documents before inserting (`--objcheck`). | `True`  |
| DROP         | Replace existing objects during restore (`--drop`). | `True`  |

## Django Connector

The Django connector (`dbbackup.db.django.DjangoConnector`) provides database-agnostic backup and restore functionality using Django's built-in `dumpdata` and `loaddata` management commands. This connector works with any Django-supported database backend.

This connector is automatically used for any unmapped database engines. If needed, you can explicitly configure it:

```python
DBBACKUP_CONNECTORS = {
    'default': {
        'CONNECTOR': 'dbbackup.db.django.DjangoConnector',
    }
}
```

### Key Features

- **Universal compatibility**: Works with any database backend supported by Django
- **No external dependencies**: Uses Django's serialization system
- **Model-level backups**: Preserves foreign key relationships and data integrity
- **JSON format**: Creates human-readable backups in JSON format

### When to Use

The Django connector is ideal for:

- Oracle databases (used by default)
- Custom or third-party database backends not explicitly supported
- Development environments where simplicity is preferred
- Cases where external database tools are not available

### Limitations

- **Performance**: Slower than native database tools for large datasets
- **Database structure**: Only backs up data, not database schema, indices, or procedures

### File Extension

By default, backups use the `.json` extension.

## Custom Connectors

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
