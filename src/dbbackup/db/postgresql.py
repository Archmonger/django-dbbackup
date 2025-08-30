from __future__ import annotations

import logging
import shlex
from typing import Any, ClassVar
from urllib.parse import quote

from dbbackup.db.base import BaseCommandDBConnector

logger = logging.getLogger("dbbackup.command")


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
    host = connector.settings.get("HOST", "localhost")
    cmd_part = connector.settings.get("NAME", "")
    user = quote(connector.settings.get("USER") or "")
    password = connector.settings.get("PASSWORD", -1)
    if user:
        host = f"@{host}"
    port = f":{connector.settings.get('PORT')}" if connector.settings.get("PORT") else ""
    cmd_part = f"--dbname=postgresql://{user}{host}{port}/{cmd_part}"
    env = {}
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
        stdout, stderr = self.run_command(cmd, env={**self.dump_env, **pg_env})
        return stdout

    def _restore_dump(self, dump):
        cmd_part, pg_env = parse_postgres_settings(self)
        cmd = f"{self.restore_cmd} {cmd_part}"

        # without this, psql terminates with an exit value of 0 regardless of errors
        cmd += " --set ON_ERROR_STOP=on"

        if self.schemas:
            cmd += " -n " + " -n ".join(self.schemas)

        if self.single_transaction:
            cmd += " --single-transaction"

        cmd += f" {self.settings['NAME']}"
        cmd = f"{self.restore_prefix} {cmd} {self.restore_suffix}"
        stdout, stderr = self.run_command(cmd, stdin=dump, env={**self.restore_env, **pg_env})
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

        return self.run_command(cmd)

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

    def _restore_dump(self, dump: str):
        """
        Restore a PostgreSQL dump using subprocess with argument list.

        Assumes that restore_prefix, restore_cmd, pg_options, and restore_suffix
        are either None, strings (single args), or lists of strings.

        Builds the command as a list.
        """

        cmd_part, pg_env = parse_postgres_settings(self)
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
        stdout, _ = self.run_command(cmd_str, stdin=dump, env={**self.dump_env, **pg_env})

        return stdout
