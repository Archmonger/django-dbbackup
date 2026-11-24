import os
import shlex
import sys
from tempfile import SpooledTemporaryFile
from unittest.mock import patch

import pytest
from django.test import TestCase

from dbbackup import settings as dbbackup_settings
from dbbackup.db import exceptions
from dbbackup.db.base import BaseCommandDBConnector, BaseDBConnector, _split_command, get_connector


class GetConnectorTest(TestCase):
    def test_get_connector(self):
        connector = get_connector()
        assert isinstance(connector, BaseDBConnector)

    @patch.dict("dbbackup.settings.CONNECTORS", {}, clear=True)
    def test_get_connector_sqlite_uses_backup_connector(self):
        """Test that SQLite database uses SqliteBackupConnector as default."""
        from unittest.mock import patch

        from dbbackup.db.sqlite import SqliteBackupConnector

        # Mock the database connection to simulate SQLite
        mock_connection = {"ENGINE": "django.db.backends.sqlite3"}

        with patch("django.db.connections") as mock_connections:
            mock_connections.__getitem__.return_value.settings_dict = mock_connection
            connector = get_connector()
            assert isinstance(connector, SqliteBackupConnector)

    @patch.dict("dbbackup.settings.CONNECTORS", {}, clear=True)
    def test_get_connector_oracle_fallback(self):
        """Test that Oracle database uses Django connector as fallback."""
        from unittest.mock import patch

        from dbbackup.db.django import DjangoConnector

        # Mock the database connection to simulate Oracle
        mock_connection = {"ENGINE": "django.db.backends.oracle"}

        with patch("django.db.connections") as mock_connections:
            mock_connections.__getitem__.return_value.settings_dict = mock_connection
            connector = get_connector()
            assert isinstance(connector, DjangoConnector)

    @patch.dict("dbbackup.settings.CONNECTORS", {}, clear=True)
    def test_get_connector_unmapped_engine_fallback(self):
        """Test that unmapped database engines use Django connector as fallback."""
        from unittest.mock import patch

        from dbbackup.db.django import DjangoConnector

        # Mock the database connection to simulate an unmapped engine
        mock_connection = {"ENGINE": "some.custom.database.backend"}

        with patch("django.db.connections") as mock_connections:
            mock_connections.__getitem__.return_value.settings_dict = mock_connection
            connector = get_connector()
            assert isinstance(connector, DjangoConnector)

    def test_get_connector_explicit_connector_path(self):
        """Test get_connector with explicit connector_path parameter."""
        from dbbackup.db.sqlite import SqliteBackupConnector

        connector = get_connector("default", connector_path="dbbackup.db.sqlite.SqliteBackupConnector")
        assert isinstance(connector, SqliteBackupConnector)

    def test_get_connector_applies_connector_settings(self):
        """Test that get_connector applies kwargs from DBBACKUP_CONNECTORS."""
        from dbbackup.db.sqlite import SqliteBackupConnector

        configured = dict(dbbackup_settings.CONNECTORS)
        # Patch the mapping itself instead of reloading dbbackup.settings: connectors read
        # CONNECTORS at call time, and reloading the module leaks the override into every
        # test that runs afterwards in the same session.
        with patch.dict(dbbackup_settings.CONNECTORS, {"default": {"RESTORE_SUFFIX": " --skip-ssl"}}, clear=True):
            connector = get_connector("default", connector_path="dbbackup.db.sqlite.SqliteBackupConnector")

        assert isinstance(connector, SqliteBackupConnector)
        assert connector.restore_suffix == " --skip-ssl"
        # The mapping must be left untouched for the rest of the session.
        assert dbbackup_settings.CONNECTORS == configured


class BaseDBConnectorTest(TestCase):
    def test_init(self):
        BaseDBConnector()

    def test_settings(self):
        connector = BaseDBConnector()
        assert isinstance(connector.settings, dict)

    def test_generate_filename(self):
        connector = BaseDBConnector()
        connector.generate_filename()

    def test_exclude_is_not_shared_between_instances(self):
        """Mutating exclude must not leak through the class attribute."""
        first = BaseDBConnector()
        second = BaseDBConnector()

        # What `dbbackup --exclude-tables` does, once per database of a `-d a,b` run.
        first.exclude.extend(["django_session", "temp_data"])

        assert first.exclude == ["django_session", "temp_data"]
        assert second.exclude == []
        assert BaseDBConnector.exclude == []

    def test_connector_settings_are_not_aliased(self):
        """DBBACKUP_CONNECTORS values must be copied onto the connector, not bound."""
        options = {"EXCLUDE": ["django_session"], "ENV": {"FOO": "bar"}}
        with patch.dict("dbbackup.settings.CONNECTORS", {"default": options}, clear=True):
            connector = get_connector("default", connector_path="dbbackup.db.mysql.MysqlDumpConnector")

        connector.exclude.append("temp_data")
        connector.env["BAZ"] = "qux"

        assert options["EXCLUDE"] == ["django_session"]
        assert options["ENV"] == {"FOO": "bar"}
        assert connector.exclude == ["django_session", "temp_data"]
        assert connector.env == {"FOO": "bar", "BAZ": "qux"}


class BaseCommandDBConnectorTest(TestCase):
    def test_run_command(self):
        connector = BaseCommandDBConnector()
        stdout, stderr = connector.run_command("echo 123")
        assert stdout.read() == b"123\n"
        assert stderr.read() == b""

    def test_run_command_error(self):
        connector = BaseCommandDBConnector()
        with pytest.raises(exceptions.CommandConnectorError):
            connector.run_command("echa 123")

    def test_run_command_error_message_for_missing_command(self):
        """Test error message when a database command is not found."""
        connector = BaseCommandDBConnector()
        with pytest.raises(exceptions.CommandConnectorError) as cm:
            connector.run_command("nonexistent_database_command_12345")

        error_message = str(cm.value)

        # Check that the improved error message contains helpful information
        assert "Database command 'nonexistent_database_command_12345' not found" in error_message
        assert "Please ensure the required database client tools are installed" in error_message
        assert "PostgreSQL: Install postgresql-client" in error_message
        assert "MySQL: Install mysql-client" in error_message
        assert "MongoDB: Install mongodb-tools" in error_message
        assert "DUMP_CMD: Path to the dump command" in error_message
        assert "RESTORE_CMD: Path to the restore command" in error_message

    def test_run_command_error_message_for_other_os_errors(self):
        """Test that non-ENOENT OSErrors still get the original error format."""
        connector = BaseCommandDBConnector()

        # Mock OSError with a different errno to test the else branch
        with patch("dbbackup.db.base.Popen") as mock_popen:
            mock_popen.side_effect = OSError(13, "Permission denied")  # EACCES

            with pytest.raises(exceptions.CommandConnectorError) as cm:
                connector.run_command("some_command")

            error_message = str(cm.value)

            # Should get the original error format for non-ENOENT errors
            assert "Error running: some_command" in error_message
            assert "Permission denied" in error_message
            # Should NOT contain the helpful database installation message
            assert "Database command" not in error_message
            assert "client tools are installed" not in error_message

    @patch("dbbackup.db.base.os.name", "nt")
    def test_split_command_keeps_backslashes_on_windows(self):
        command = r'"C:\Program Files\PostgreSQL\bin\psql.exe" C:\pgsql\bin\pg_dump.exe ' + shlex.quote("p w")
        assert _split_command(command) == [
            r"C:\Program Files\PostgreSQL\bin\psql.exe",
            r"C:\pgsql\bin\pg_dump.exe",
            "p w",
        ]

    @patch("dbbackup.db.base.os.name", "posix")
    def test_split_command_posix(self):
        command = r"pg_dump a\ b 'c d' \"e\""
        assert _split_command(command) == shlex.split(command)

    @pytest.mark.skipif(os.name != "nt", reason="Windows command line")
    def test_run_command_windows_path(self):
        connector = BaseCommandDBConnector()
        stdout, _stderr = connector.run_command(
            rf'"{sys.executable}" -c "import sys; print(sys.argv[1])" C:\dumps\db.psql'
        )
        assert stdout.read().strip() == rb"C:\dumps\db.psql"

    def test_run_command_stdin(self):
        connector = BaseCommandDBConnector()
        stdin = SpooledTemporaryFile()
        stdin.write(b"foo")
        stdin.seek(0)
        # Run
        stdout, stderr = connector.run_command("cat", stdin=stdin)
        assert stdout.read() == b"foo"
        assert not stderr.read()

    def test_run_command_with_env(self):
        connector = BaseCommandDBConnector()
        # Empty env
        stdout, _stderr = connector.run_command("env")
        assert stdout.read()
        # env from self.env
        connector.env = {"foo": "bar"}
        stdout, _stderr = connector.run_command("env")
        assert b"foo=bar\n" in stdout.read()
        # method override global env
        stdout, _stderr = connector.run_command("env", env={"foo": "ham"})
        assert b"foo=ham\n" in stdout.read()
        # get a var from parent env
        os.environ["BAR"] = "foo"
        stdout, _stderr = connector.run_command("env")
        assert b"bar=foo\n" in stdout.read()
        # Conf overrides parendt env
        connector.env = {"bar": "bar"}
        stdout, _stderr = connector.run_command("env")
        assert b"bar=bar\n" in stdout.read()
        # method overrides all
        stdout, _stderr = connector.run_command("env", env={"bar": "ham"})
        assert b"bar=ham\n" in stdout.read()

    def test_run_command_with_parent_env(self):
        connector = BaseCommandDBConnector(use_parent_env=False)
        # Empty env
        stdout, _stderr = connector.run_command("env")
        assert not stdout.read()
        # env from self.env
        connector.env = {"foo": "bar"}
        stdout, _stderr = connector.run_command("env")
        assert stdout.read() == b"foo=bar\n"
        # method override global env
        stdout, _stderr = connector.run_command("env", env={"foo": "ham"})
        assert stdout.read() == b"foo=ham\n"
        # no var from parent env
        os.environ["BAR"] = "foo"
        stdout, _stderr = connector.run_command("env")
        assert b"bar=foo\n" not in stdout.read()
