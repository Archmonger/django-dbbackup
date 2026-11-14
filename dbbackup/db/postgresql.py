from __future__ import annotations

import logging
import os
import shlex
import tempfile
from contextlib import contextmanager
from typing import Any, ClassVar
from urllib.parse import quote

from dbbackup import settings
from dbbackup.db.base import BaseCommandDBConnector

logger = logging.getLogger("dbbackup.command")

# ``pg_dump`` emits a DROP DEFAULT statement in the clean section of a dump for
# every serial-backed column. When the target table now uses an identity column,
# PostgreSQL rejects that statement, so the identity property has to be removed
# first. The replacement is a no-op on columns which are not identity columns,
# which keeps serial-to-serial restores working.
_DROP_DEFAULT_SUFFIX = b" DROP DEFAULT;"
_DROP_IDENTITY_SUFFIX = b" DROP IDENTITY IF EXISTS;"


def _identity_prelude_from_sql(sql: bytes) -> bytes:
    """Build DROP IDENTITY statements for the DROP DEFAULT statements in *sql*."""
    prelude = []
    for line in sql.splitlines(keepends=True):
        stripped = line.strip()
        if (
            stripped.startswith(b"ALTER TABLE ")
            and b" ALTER COLUMN " in stripped
            and stripped.endswith(_DROP_DEFAULT_SUFFIX)
        ):
            prelude.append(
                stripped[: -len(_DROP_DEFAULT_SUFFIX)] + _DROP_IDENTITY_SUFFIX + b"\n"
            )
    return b"".join(prelude)


def _identity_prelude_from_text_dump(dump) -> bytes:
    """Build DROP IDENTITY statements from the clean section of a text dump."""
    prelude = []
    for line in dump:
        stripped = line.strip()
        # The clean section precedes the objects it drops. Once the first object
        # is created (or data is copied) there is nothing left to fix.
        if stripped.startswith((b"CREATE ", b"COPY ", b"INSERT INTO ")):
            break
        if (
            stripped.startswith(b"ALTER TABLE ")
            and b" ALTER COLUMN " in stripped
            and stripped.endswith(_DROP_DEFAULT_SUFFIX)
        ):
            prelude.append(
                stripped[: -len(_DROP_DEFAULT_SUFFIX)] + _DROP_IDENTITY_SUFFIX + b"\n"
            )
    return b"".join(prelude)


@contextmanager
def _identity_prelude_file(prelude: bytes):
    """Write *prelude* to a temporary SQL file and yield its path."""
    fd, path = tempfile.mkstemp(
        prefix="dbbackup_identity_", suffix=".sql", dir=settings.TMP_DIR
    )
    try:
        with os.fdopen(fd, "wb") as prelude_file:
            prelude_file.write(prelude)
        yield path
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

# Connection options understood by the PostgreSQL command line tools, mapped to
# the ``libpq`` environment variable carrying each one. It mirrors
# ``settings_to_cmd_args_env`` in ``django/db/backends/postgresql/client.py``,
# so that ``pg_dump``, ``psql`` and ``pg_restore`` connect with the same TLS,
# client certificate, password file and service settings as the ORM does.
PG_OPTIONS_ENV_VARS: dict[str, str] = {
    "sslmode": "PGSSLMODE",
    "sslrootcert": "PGSSLROOTCERT",
    "sslcert": "PGSSLCERT",
    "sslkey": "PGSSLKEY",
    "passfile": "PGPASSFILE",
    "service": "PGSERVICE",
}


def _host_requires_uri_quoting(host: str) -> bool:
    # Match *nix paths (e.g. /run/postgres) and Windows paths (e.g. C:\path\to\socket)
    return host.startswith(("/", "@")) or (
        len(host) >= 3 and host[0].isalpha() and host[1] == ":" and host[2] in ("/", "\\")
    )


def parse_postgres_options_env(connector: PgDumpBinaryConnector | PgDumpConnector) -> dict[str, str]:
    """
    Translate the ``OPTIONS`` setting of a Postgres connection into the ``libpq``
    environment variables understood by the command line tools.

    The options are passed through the environment rather than appended to the
    connection URI because ``libpq`` expands ``%XX`` triplets only: a path
    encoded with ``quote_plus`` semantics would reach the tools with its spaces
    turned into ``+`` and would not be found.

    Args:
        connector: Database connector instance with settings

    Returns:
        dict: Environment variables to apply to the command
    """
    options = connector.settings.get("OPTIONS") or {}
    return {env_var: str(options[option]) for option, env_var in PG_OPTIONS_ENV_VARS.items() if options.get(option)}


def parse_postgres_settings(connector: PgDumpBinaryConnector | PgDumpConnector) -> tuple[str, dict[Any, Any]]:
    """
    Parse the common Postgres connectors settings and
    generate a portion of the command string and any
    relevant environment variables.

    Args:
        connector: Database connector instance with settings

    Returns:
        tuple: (cmd_part, environment_dict)
    """
    host = connector.settings.get("HOST")
    if host is None:
        host = "localhost"
    elif _host_requires_uri_quoting(host):
        host = quote(host, safe="")
    cmd_part = connector.settings.get("NAME", "")
    user = quote(connector.settings.get("USER") or "")
    password = connector.settings.get("PASSWORD", -1)
    if user:
        host = f"@{host}"
    port = f":{connector.settings.get('PORT')}" if connector.settings.get("PORT") else ""
    cmd_part = f"--dbname=postgresql://{user}{host}{port}/{cmd_part}"
    env = parse_postgres_options_env(connector)
    if password is None:
        cmd_part += " --no-password"
    elif password not in ("", -1):
        env["PGPASSWORD"] = password
    return cmd_part, env


class PgDumpConnector(BaseCommandDBConnector):
    """
    PostgreSQL connector, it uses `pg_dump` to create an SQL text file
    and `psql` for restore it.
    """

    extension = "psql"
    dump_cmd = "pg_dump"
    restore_cmd = "psql"
    single_transaction = True
    drop = True
    if_exists = True
    schemas: ClassVar[list[str] | None] = []

    def _create_dump(self):
        cmd_part, pg_env = parse_postgres_settings(self)
        cmd = f"{self.dump_cmd} {cmd_part}"

        for table in self.exclude:
            cmd += f" --exclude-table-data={table}"

        if self.drop:
            cmd += " --clean"

        if self.if_exists or self.drop:
            cmd += " --if-exists"

        if self.schemas:
            # First schema is not prefixed with -n
            # when using join function so add it manually.
            cmd += " -n " + " -n ".join(self.schemas)

        cmd = f"{self.dump_prefix} {cmd} {self.dump_suffix}"
        stdout, _stderr = self.run_command(cmd, env={**self.dump_env, **pg_env})
        return stdout

    def _target_has_identity_columns(self) -> bool:
        """
        Return whether the target database contains identity columns.

        A dump created from serial columns only fails when it is restored over a
        table which now uses an identity column, so the extra restore work is
        skipped for databases without identity columns.
        """
        if self.connection.vendor != "postgresql":
            return False

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM pg_catalog.pg_attribute "
                    "WHERE attidentity IN ('a', 'd') AND NOT attisdropped"
                    ")"
                )
                row = cursor.fetchone()
            return bool(row and row[0])
        except Exception:
            logger.warning(
                "Could not check the target database for identity columns; "
                "using the standard restore command.",
                exc_info=True,
            )
            return False

    def _restore_dump(self, dump):
        cmd_part, pg_env = parse_postgres_settings(self)
        cmd = f"{self.restore_cmd} {cmd_part}"

        # without this, psql terminates with an exit value of 0 regardless of errors
        cmd += " --set ON_ERROR_STOP=on"

        if self.schemas:
            cmd += " -n " + " -n ".join(self.schemas)

        if self.single_transaction:
            cmd += " --single-transaction"

        prelude = b""
        if self._target_has_identity_columns():
            # Text dumps carry their clean statements inside the file, so they
            # must be handled even when the restore is told not to drop objects.
            prelude = _identity_prelude_from_text_dump(dump)
            dump.seek(0)

        if not prelude:
            cmd += f" {self.settings['NAME']}"
            cmd = f"{self.restore_prefix} {cmd} {self.restore_suffix}"
            stdout, stderr = self.run_command(
                cmd, stdin=dump, env={**self.restore_env, **pg_env}
            )
            return stdout, stderr

        # Run the generated statements and the dump in a single psql session, so
        # the identity properties are dropped inside the same transaction as the
        # restore and rolled back if the restore fails.
        with _identity_prelude_file(prelude) as prelude_path:
            cmd += f" -f {shlex.quote(prelude_path)} -f - {self.settings['NAME']}"
            cmd = f"{self.restore_prefix} {cmd} {self.restore_suffix}"
            stdout, stderr = self.run_command(
                cmd, stdin=dump, env={**self.restore_env, **pg_env}
            )
            return stdout, stderr


class PgDumpGisConnector(PgDumpConnector):
    """
    PostgreGIS connector, same than :class:`PgDumpGisConnector` but enable
    postgis if not made.
    """

    psql_cmd = "psql"

    def _enable_postgis(self):
        cmd = f'{self.psql_cmd} -c "CREATE EXTENSION IF NOT EXISTS postgis;"'
        cmd += f" --username={shlex.quote(self.settings['ADMIN_USER'])}"
        cmd += " --no-password"

        if self.settings.get("HOST"):
            cmd += f" --host={shlex.quote(self.settings['HOST'])}"

        if self.settings.get("PORT"):
            cmd += f" --port={shlex.quote(str(self.settings['PORT']))}"

        # This is a separate psql invocation: it needs the same TLS settings as
        # the restore it precedes, otherwise it cannot authenticate with a
        # client certificate and the PostGIS activation fails.
        env = {**self.restore_env, **parse_postgres_options_env(self)}
        # "--no-password" only forbids the interactive prompt, libpq still
        # reads PGPASSWORD, so the credentials of ADMIN_USER go there.
        admin_password = self.settings.get("ADMIN_PASSWORD")
        if admin_password:
            env["PGPASSWORD"] = str(admin_password)

        return self.run_command(cmd, env=env)

    def _restore_dump(self, dump):
        if self.settings.get("ADMIN_USER"):
            self._enable_postgis()
        return super()._restore_dump(dump)


class PgDumpBinaryConnector(PgDumpConnector):
    """
    PostgreSQL connector, it uses `pg_dump` to create an SQL text file
    and `pg_restore` for restore it.
    """

    extension = "psql.bin"
    dump_cmd = "pg_dump"
    restore_cmd = "pg_restore"
    psql_cmd = "psql"
    single_transaction = True
    drop = True
    if_exists = True
    pg_options = None

    def _create_dump(self):
        cmd_part, pg_env = parse_postgres_settings(self)
        cmd = f"{self.dump_cmd} {cmd_part}"

        cmd += " --format=custom"
        for table in self.exclude:
            cmd += f" --exclude-table-data={table}"

        if self.schemas:
            cmd += " -n " + " -n ".join(self.schemas)

        cmd = f"{self.dump_prefix} {cmd} {self.dump_suffix}"
        stdout, _ = self.run_command(cmd, env={**self.dump_env, **pg_env})
        return stdout

    def _pg_options_allow_sql_generation(self) -> bool:
        """
        Return whether ``pg_options`` can be combined with ``pg_restore -f``.

        ``--jobs`` and ``--dbname`` are incompatible with writing the archive to
        standard output, which the identity-column restore requires.
        """
        options = self.pg_options or []
        if isinstance(options, str):
            options = shlex.split(options)

        for option in options:
            if option in ("-j", "--jobs", "-d", "--dbname"):
                return False
            if option.startswith(("--jobs=", "--dbname=")):
                return False
            if option.startswith("-j") and not option.startswith("--"):
                return False
            if option.startswith("-d") and not option.startswith("--"):
                return False

        return True

    def _pg_options_tokens(self) -> list[str]:
        """Return ``pg_options`` as a list of command line arguments."""
        options = self.pg_options or []
        if isinstance(options, str):
            return shlex.split(options)
        return list(options)

    def _pg_options_select_pre_data(self) -> bool:
        """
        Return whether ``pg_options`` restores the pre-data section.

        Only the pre-data section contains the clean statements which drop
        serial defaults, so the identity-column workaround is unnecessary when
        the caller restores data or post-data only.
        """
        options = self._pg_options_tokens()
        if "-a" in options or "--data-only" in options:
            return False

        sections = []
        for index, option in enumerate(options):
            if option == "--section":
                if index + 1 < len(options):
                    sections.append(options[index + 1])
            elif option.startswith("--section="):
                sections.append(option.split("=", 1)[1])

        return not sections or "pre-data" in sections

    def _pg_options_single_transaction(self) -> bool:
        """Return whether ``pg_options`` asks for a single transaction."""
        return any(
            option in ("-1", "--single-transaction")
            for option in self._pg_options_tokens()
        )

    def _build_pg_restore_sql_cmd(self, pre_data: bool = False) -> str:
        """Build a ``pg_restore`` command which writes SQL to standard output."""
        cmd = []
        if self.restore_prefix:
            cmd.extend(
                self.restore_prefix
                if isinstance(self.restore_prefix, list)
                else [self.restore_prefix]
            )
        if self.restore_cmd:
            cmd.extend(
                self.restore_cmd
                if isinstance(self.restore_cmd, list)
                else [self.restore_cmd]
            )
        if self.pg_options:
            # ``--single-transaction`` only wraps the generated SQL in
            # BEGIN/COMMIT. The prelude has to run in the same transaction as
            # the dump, so the psql invocation owns transaction handling.
            options = [
                option
                for option in self._pg_options_tokens()
                if option not in ("-1", "--single-transaction")
            ]
            if options:
                cmd.append(" ".join(shlex.quote(option) for option in options))

        cmd.extend(["-f", "-"])

        if self.drop:
            cmd.append("--clean")

        if self.schemas:
            for schema in self.schemas:
                cmd.extend(["-n", schema])

        if self.if_exists or self.drop:
            cmd.append("--if-exists")

        if pre_data:
            cmd.append("--section=pre-data")

        return " ".join(cmd)

    def _identity_prelude_from_archive(self, dump, pg_env) -> bytes:
        """Return the DROP IDENTITY statements needed by the archive in *dump*."""
        cmd = self._build_pg_restore_sql_cmd(pre_data=True)
        stdout, _ = self.run_command(cmd, stdin=dump, env={**self.restore_env, **pg_env})
        dump.seek(0)
        return _identity_prelude_from_sql(stdout.read())

    def _restore_dump_with_identity_prelude(self, dump, prelude, cmd_part, pg_env):
        """Generate the dump's SQL and restore it together with the prelude."""
        full_sql, _ = self.run_command(
            self._build_pg_restore_sql_cmd(),
            stdin=dump,
            env={**self.restore_env, **pg_env},
        )

        with _identity_prelude_file(prelude) as prelude_path:
            cmd = []
            if self.restore_prefix:
                cmd.extend(
                    self.restore_prefix
                    if isinstance(self.restore_prefix, list)
                    else [self.restore_prefix]
                )
            cmd.append(self.psql_cmd)
            cmd.append(cmd_part)
            cmd.extend(["--set", "ON_ERROR_STOP=on"])
            if self.single_transaction or self._pg_options_single_transaction():
                cmd.append("--single-transaction")
            cmd.extend(["-f", shlex.quote(prelude_path), "-f", "-"])
            if self.restore_suffix:
                cmd.extend(
                    self.restore_suffix
                    if isinstance(self.restore_suffix, list)
                    else [self.restore_suffix]
                )

            stdout, _ = self.run_command(
                " ".join(cmd), stdin=full_sql, env={**self.restore_env, **pg_env}
            )
            return stdout

    def _restore_dump(self, dump: str):
        """
        Restore a PostgreSQL dump using subprocess with argument list.

        Assumes that restore_prefix, restore_cmd, pg_options, and restore_suffix
        are either None, strings (single args), or lists of strings.

        Builds the command as a list.
        """

        cmd_part, pg_env = parse_postgres_settings(self)

        if (
            self.drop
            and self._target_has_identity_columns()
            and self._pg_options_allow_sql_generation()
            and self._pg_options_select_pre_data()
        ):
            prelude = self._identity_prelude_from_archive(dump, pg_env)
            if prelude:
                return self._restore_dump_with_identity_prelude(
                    dump, prelude, cmd_part, pg_env
                )

        cmd = []

        # Flatten optional values
        if self.restore_prefix:
            cmd.extend(self.restore_prefix if isinstance(self.restore_prefix, list) else [self.restore_prefix])

        if self.restore_cmd:
            cmd.extend(self.restore_cmd if isinstance(self.restore_cmd, list) else [self.restore_cmd])

        if self.pg_options:
            cmd.extend(self.pg_options if isinstance(self.pg_options, list) else [self.pg_options])

        cmd.extend([cmd_part])

        if self.single_transaction:
            cmd.extend(["--single-transaction"])

        if self.drop:
            cmd.extend(["--clean"])

        if self.schemas:
            for schema in self.schemas:
                cmd.extend(["-n", schema])

        if self.if_exists or self.drop:
            cmd.extend(["--if-exists"])

        if self.restore_suffix:
            cmd.extend(self.restore_suffix if isinstance(self.restore_suffix, list) else [self.restore_suffix])

        cmd_str = " ".join(cmd)
        stdout, _ = self.run_command(cmd_str, stdin=dump, env={**self.restore_env, **pg_env})

        return stdout
