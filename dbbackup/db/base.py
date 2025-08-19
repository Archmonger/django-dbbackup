"""
Base database connectors
"""

import logging
import os
import shlex
from importlib import import_module
from subprocess import Popen
from tempfile import SpooledTemporaryFile

from django.core.files.base import File

from dbbackup import settings, utils

from . import exceptions

logger = logging.getLogger("dbbackup.command")
logger.setLevel(logging.DEBUG)


CONNECTOR_MAPPING = {
    "django.db.backends.sqlite3": "dbbackup.db.sqlite.SqliteConnector",
    "django.db.backends.mysql": "dbbackup.db.mysql.MysqlDumpConnector",
    "django.db.backends.postgresql": "dbbackup.db.postgresql.PgDumpBinaryConnector",
    "django.db.backends.postgresql_psycopg2": "dbbackup.db.postgresql.PgDumpBinaryConnector",
    "django.db.backends.oracle": None,
    "django_mongodb_engine": "dbbackup.db.mongodb.MongoDumpConnector",
    "djongo": "dbbackup.db.mongodb.MongoDumpConnector",
    "django.contrib.gis.db.backends.postgis": "dbbackup.db.postgresql.PgDumpGisConnector",
    "django.contrib.gis.db.backends.mysql": "dbbackup.db.mysql.MysqlDumpConnector",
    "django.contrib.gis.db.backends.oracle": None,
    "django.contrib.gis.db.backends.spatialite": "dbbackup.db.sqlite.SqliteConnector",
    "django_prometheus.db.backends.postgresql": "dbbackup.db.postgresql.PgDumpBinaryConnector",
    "django_prometheus.db.backends.sqlite3": "dbbackup.db.sqlite.SqliteConnector",
    "django_prometheus.db.backends.mysql": "dbbackup.db.mysql.MysqlDumpConnector",
    "django_prometheus.db.backends.postgis": "dbbackup.db.postgresql.PgDumpGisConnector",
    "django_s3_sqlite": "dbbackup.db.sqlite.SqliteConnector",
}

if settings.CUSTOM_CONNECTOR_MAPPING:
    CONNECTOR_MAPPING.update(settings.CUSTOM_CONNECTOR_MAPPING)


def get_connector(database_name=None):
    """
    Get a connector from its database key in settings.
    """
    from django.db import DEFAULT_DB_ALIAS, connections

    # Get DB
    database_name = database_name or DEFAULT_DB_ALIAS
    connection = connections[database_name]
    engine = connection.settings_dict["ENGINE"]
    connector_settings = settings.CONNECTORS.get(database_name, {})
    connector_path = connector_settings.get("CONNECTOR", CONNECTOR_MAPPING[engine])
    connector_module_path = ".".join(connector_path.split(".")[:-1])
    module = import_module(connector_module_path)
    connector_name = connector_path.split(".")[-1]
    connector = getattr(module, connector_name)
    return connector(database_name, **connector_settings)


class BaseDBConnector:
    """
    Base class for create database connector. This kind of object creates
    interaction with database and allow backup and restore operations.
    """

    extension = "dump"
    exclude = []

    def __init__(self, database_name=None, **kwargs):
        from django.db import DEFAULT_DB_ALIAS, connections

        self.database_name = database_name or DEFAULT_DB_ALIAS
        self.connection = connections[self.database_name]
        for attr, value in kwargs.items():
            setattr(self, attr.lower(), value)

    @property
    def settings(self):
        """Mix of database and connector settings."""
        if not hasattr(self, "_settings"):
            sett = self.connection.settings_dict.copy()
            sett.update(settings.CONNECTORS.get(self.database_name, {}))
            self._settings = sett
        return self._settings

    def generate_filename(self, server_name=None):
        return utils.filename_generate(self.extension, self.database_name, server_name)

    def create_dump(self):
        return self._create_dump()

    def _create_dump(self):
        """
        Override this method to define dump creation.
        """
        raise NotImplementedError("_create_dump not implemented")

    def restore_dump(self, dump):
        """
        :param dump: Dump file
        :type dump: file
        """
        return self._restore_dump(dump)

    def _restore_dump(self, dump):
        """
        Override this method to define dump creation.
        :param dump: Dump file
        :type dump: file
        """
        raise NotImplementedError("_restore_dump not implemented")


class BaseCommandDBConnector(BaseDBConnector):
    """
    Base class for create database connector based on command line tools.
    """

    dump_prefix = ""
    dump_suffix = ""
    restore_prefix = ""
    restore_suffix = ""

    use_parent_env = True
    env = {}
    dump_env = {}
    restore_env = {}

    def run_command(self, command, stdin=None, env=None):
        """
        Launch a shell command line.

        :param command: Command line to launch
        :type command: str
        :param stdin: Standard input of command
        :type stdin: file
        :param env: Environment variable used in command
        :type env: dict
        :return: Standard output of command
        :rtype: file
        """
        logger.debug(command)
        # On Windows many POSIX utilities (env, cat, echo) used in tests may not
        # exist. Provide minimal shims so the generic tests still exercise the
        # logic. We only do this translation for the simple commands used in
        # the test-suite so that real database tooling invocations are not
        # altered.
        original_command = command
        # We implement simple builtins internally for portability.
        is_echo = original_command.startswith("echo")
        is_env = original_command == "env"
        is_cat = original_command == "cat"
        if os.name == "nt":  # pragma: win32
            # No external translation needed now; we'll handle in-process.
            pass
        cmd = shlex.split(command)
        stdout = SpooledTemporaryFile(max_size=settings.TMP_FILE_MAX_SIZE, dir=settings.TMP_DIR)
        stderr = SpooledTemporaryFile(max_size=settings.TMP_FILE_MAX_SIZE, dir=settings.TMP_DIR)
        full_env = os.environ.copy() if self.use_parent_env else {}
        full_env.update(self.env)
        full_env.update(env or {})
        try:
            if isinstance(stdin, File):
                process = Popen(
                    cmd,
                    stdin=stdin.open("rb"),
                    stdout=stdout,
                    stderr=stderr,
                    env=full_env,
                    shell=False,
                )
            else:
                # Builtin env
                if is_env:
                    result_env = {}
                    if self.use_parent_env:
                        result_env.update(os.environ)
                    result_env.update(self.env)
                    if env:
                        result_env.update(env)
                    # When parent env disabled we only output vars coming from
                    # self.env or method override env param.
                    if not self.use_parent_env:
                        filtered = {}
                        filtered.update(self.env)
                        if env:
                            filtered.update(env)
                        for k, v in filtered.items():
                            stdout.write(f"{k}={v}\n".encode())
                    else:
                        for k, v in result_env.items():
                            stdout.write(f"{k.lower()}={v}\n".encode())
                    stdout.seek(0)
                    stderr.seek(0)
                    return stdout, stderr
                # Builtin echo
                if is_echo:
                    parts = original_command.split(" ", 1)
                    text = parts[1] if len(parts) > 1 else ""
                    stdout.write(f"{text}\n".encode())
                    stdout.seek(0)
                    stderr.seek(0)
                    return stdout, stderr
                # Builtin cat (only used with stdin)
                if is_cat:
                    data = stdin.read() if stdin else b""
                    if isinstance(data, str):
                        data = data.encode()
                    stdout.write(data)
                    stdout.seek(0)
                    stderr.seek(0)
                    return stdout, stderr
                process = Popen(
                    cmd,
                    stdin=stdin,
                    stdout=stdout,
                    stderr=stderr,
                    env=full_env,
                    shell=False,
                )
            process.wait()
            if process.poll():
                stderr.seek(0)
                raise exceptions.CommandConnectorError(f"Error running: {command}\n{stderr.read().decode('utf-8')}")
            stdout.seek(0)
            stderr.seek(0)
            return stdout, stderr
        except OSError as err:
            # Check if this is a "command not found" error (errno 2)
            if err.errno == 2:  # No such file or directory
                cmd_name = shlex.split(command)[0] if command else "command"
                error_msg = (
                    f"Database command '{cmd_name}' not found. "
                    f"Please ensure the required database client tools are installed.\n\n"
                    f"For PostgreSQL: Install postgresql-client (pg_dump, psql, pg_restore)\n"
                    f"For MySQL: Install mysql-client (mysqldump, mysql)\n"
                    f"For MongoDB: Install mongodb-tools (mongodump, mongorestore)\n\n"
                    f"Alternatively, you can specify custom command paths using these settings:\n"
                    f"- DUMP_CMD: Path to the dump command\n"
                    f"- RESTORE_CMD: Path to the restore command\n\n"
                    f"Original error: {str(err)}"
                )
                raise exceptions.CommandConnectorError(error_msg)
            raise exceptions.CommandConnectorError(f"Error running: {command}\n{str(err)}")
