import logging
from typing import List, Optional
from urllib.parse import quote

from .base import BaseCommandDBConnector

logger = logging.getLogger("dbbackup.command")


def create_postgres_dbname_and_env(self):
    host = self.settings.get("HOST", "localhost")
    dbname = self.settings.get("NAME", "")
    user = quote(self.settings.get("USER") or "")
    if user:
        host = "@" + host
    port = ":{}".format(self.settings.get("PORT")) if self.settings.get("PORT") else ""
    dbname = f"--dbname=postgresql://{user}{host}{port}/{dbname}"
    env = {}
    if self.settings.get("PASSWORD"):
        env["PGPASSWORD"] = self.settings.get("PASSWORD")
    return dbname, env


class PgDumpConnector(BaseCommandDBConnector):
    """
    PostgreSQL connector, it uses pg_dump`` to create an SQL text file
    and ``psql`` for restore it.
    """

    extension = "psql"
    dump_cmd = "pg_dump"
    restore_cmd = "psql"
    single_transaction = True
    drop = True
    enable_row_security = False
    schemas: Optional[List[str]] = []

    def _create_dump(self):
        cmd = f"{self.dump_cmd} "
        dbname, pg_env = create_postgres_dbname_and_env(self)
        cmd = cmd + dbname

        for table in self.exclude:
            cmd += f" --exclude-table-data={table}"

        if self.drop:
            cmd += " --clean"

        if self.enable_row_security:
            cmd += " --enable-row-security"

        if self.schemas:
            # First schema is not prefixed with -n
            # when using join function so add it manually.
            cmd += " -n " + " -n ".join(self.schemas)

        cmd = f"{self.dump_prefix} {cmd} {self.dump_suffix}"
        stdout, stderr = self.run_command(cmd, env={**self.dump_env, **pg_env})
        return stdout

    def _restore_dump(self, dump):
        cmd = f"{self.restore_cmd} "
        dbname, pg_env = create_postgres_dbname_and_env(self)
        cmd = cmd + dbname

        # without this, psql terminates with an exit value of 0 regardless of errors
        cmd += " --set ON_ERROR_STOP=on"

        if self.schemas:
            cmd += " -n " + " -n ".join(self.schemas)

        if self.single_transaction:
            cmd += " --single-transaction"

        cmd += " {}".format(self.settings["NAME"])
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
        cmd += " --username={}".format(self.settings["ADMIN_USER"])
        cmd += " --no-password"

        if self.settings.get("HOST"):
            cmd += " --host={}".format(self.settings["HOST"])

        if self.settings.get("PORT"):
            cmd += " --port={}".format(self.settings["PORT"])

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
    if_exists = False
    enable_row_security = False
    pg_options = None

    def _create_dump(self):
        cmd = f"{self.dump_cmd} "
        dbname, pg_env = create_postgres_dbname_and_env(self)
        cmd = cmd + dbname

        cmd += " --format=custom"
        for table in self.exclude:
            cmd += f" --exclude-table-data={table}"

        if self.enable_row_security:
            cmd += " --enable-row-security"

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

        dbname, pg_env = create_postgres_dbname_and_env(self)
        cmd = []

        # Flatten optional values
        if self.restore_prefix:
            cmd.extend(self.restore_prefix if isinstance(self.restore_prefix, list) else [self.restore_prefix])

        if self.restore_cmd:
            cmd.extend(self.restore_cmd if isinstance(self.restore_cmd, list) else [self.restore_cmd])

        if self.pg_options:
            cmd.extend(self.pg_options if isinstance(self.pg_options, list) else [self.pg_options])

        cmd.extend([dbname])

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
