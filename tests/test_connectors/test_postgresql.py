from io import BytesIO
from unittest.mock import Mock, patch

from django.test import TestCase

from dbbackup.db.postgresql import (
    PgDumpBinaryConnector,
    PgDumpConnector,
    PgDumpGisConnector,
    parse_postgres_settings,
)


@patch(
    "dbbackup.db.postgresql.PgDumpConnector.run_command",
    return_value=(BytesIO(b"foo"), BytesIO()),
)
class PgDumpConnectorTest(TestCase):
    def setUp(self):
        self.connector = PgDumpConnector()
        self.connector.settings["ENGINE"] = "django.db.backends.postgresql"
        self.connector.settings["NAME"] = "dbname"
        self.connector.settings["HOST"] = "hostname"

    def test_user_uses_special_characters(self, mock_dump_cmd):
        self.connector.settings["USER"] = "@"
        self.connector.create_dump()
        assert "postgresql://%40@hostname/dbname" in mock_dump_cmd.call_args[0][0]

    def test_create_dump(self, mock_dump_cmd):
        dump = self.connector.create_dump()
        # Test dump
        dump_content = dump.read()
        assert dump_content
        assert dump_content == b"foo"
        # Test cmd
        assert mock_dump_cmd.called

    def test_create_dump_without_host(self, mock_dump_cmd):
        # this is allowed now: https://github.com/Archmonger/django-dbbackup/issues/520
        self.connector.settings.pop("HOST", None)
        self.connector.create_dump()

    def test_password_but_no_user(self, mock_dump_cmd):
        self.connector.settings.pop("USER", None)
        self.connector.settings["PASSWORD"] = "hello"
        self.connector.create_dump()
        assert "postgresql://hostname/dbname" in mock_dump_cmd.call_args[0][0]

    def test_create_dump_host(self, mock_dump_cmd):
        # With
        self.connector.settings["HOST"] = "foo"
        self.connector.create_dump()
        assert "postgresql://foo/dbname" in mock_dump_cmd.call_args[0][0]

    def test_create_dump_port(self, mock_dump_cmd):
        # Without
        self.connector.settings.pop("PORT", None)
        self.connector.create_dump()
        assert "postgresql://hostname/dbname" in mock_dump_cmd.call_args[0][0]
        # With
        self.connector.settings["PORT"] = 42
        self.connector.create_dump()
        assert "postgresql://hostname:42/dbname" in mock_dump_cmd.call_args[0][0]

    def test_create_dump_user(self, mock_dump_cmd):
        # Without
        self.connector.settings.pop("USER", None)
        self.connector.create_dump()
        assert "postgresql://hostname/dbname" in mock_dump_cmd.call_args[0][0]
        # With
        self.connector.settings["USER"] = "foo"
        self.connector.create_dump()
        assert "postgresql://foo@hostname/dbname" in mock_dump_cmd.call_args[0][0]

    def test_create_dump_exclude(self, mock_dump_cmd):
        # Without
        self.connector.create_dump()
        assert " --exclude-table-data=" not in mock_dump_cmd.call_args[0][0]
        # With
        self.connector.exclude = ("foo",)
        self.connector.create_dump()
        assert " --exclude-table-data=foo" in mock_dump_cmd.call_args[0][0]
        # With several
        self.connector.exclude = ("foo", "bar")
        self.connector.create_dump()
        assert " --exclude-table-data=foo" in mock_dump_cmd.call_args[0][0]
        assert " --exclude-table-data=bar" in mock_dump_cmd.call_args[0][0]

    def test_create_dump_drop(self, mock_dump_cmd):
        # Without
        self.connector.drop = False
        self.connector.create_dump()
        assert " --clean" not in mock_dump_cmd.call_args[0][0]
        # With
        self.connector.drop = True
        self.connector.create_dump()
        assert " --clean" in mock_dump_cmd.call_args[0][0]

    @patch(
        "dbbackup.db.postgresql.PgDumpConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump(self, mock_dump_cmd, mock_restore_cmd):
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        # Test cmd
        assert mock_restore_cmd.called

    @patch(
        "dbbackup.db.postgresql.PgDumpConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump_user(self, mock_dump_cmd, mock_restore_cmd):
        dump = self.connector.create_dump()
        # Without
        self.connector.settings.pop("USER", None)
        self.connector.restore_dump(dump)

        assert "postgresql://hostname/dbname" in mock_restore_cmd.call_args[0][0]

        assert " --username=" not in mock_restore_cmd.call_args[0][0]
        # With
        self.connector.settings["USER"] = "foo"
        self.connector.restore_dump(dump)
        assert "postgresql://foo@hostname/dbname" in mock_restore_cmd.call_args[0][0]

    def test_create_dump_schema(self, mock_dump_cmd):
        # Without
        self.connector.create_dump()
        assert " -n " not in mock_dump_cmd.call_args[0][0]
        # With
        self.connector.schemas = ["public"]
        self.connector.create_dump()
        assert " -n public" in mock_dump_cmd.call_args[0][0]
        # With several
        self.connector.schemas = ["public", "foo"]
        self.connector.create_dump()
        assert " -n public" in mock_dump_cmd.call_args[0][0]
        assert " -n foo" in mock_dump_cmd.call_args[0][0]

    @patch(
        "dbbackup.db.postgresql.PgDumpConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump_schema(self, mock_dump_cmd, mock_restore_cmd):
        # Without
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        assert " -n " not in mock_restore_cmd.call_args[0][0]
        # With
        self.connector.schemas = ["public"]
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        assert " -n public" in mock_restore_cmd.call_args[0][0]
        # With several
        self.connector.schemas = ["public", "foo"]
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        assert " -n public" in mock_restore_cmd.call_args[0][0]
        assert " -n foo" in mock_restore_cmd.call_args[0][0]

    def test_create_dump_password_excluded(self, mock_dump_cmd):
        self.connector.settings["PASSWORD"] = "secret"
        self.connector.create_dump()
        assert "secret" not in mock_dump_cmd.call_args[0][0]

    def test_restore_dump_password_excluded(self, mock_dump_cmd):
        self.connector.settings["PASSWORD"] = "secret"
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        assert "secret" not in mock_dump_cmd.call_args[0][0]


@patch(
    "dbbackup.db.postgresql.PgDumpBinaryConnector.run_command",
    return_value=(BytesIO(b"foo"), BytesIO()),
)
class PgDumpBinaryConnectorTest(TestCase):
    def setUp(self):
        self.connector = PgDumpBinaryConnector()
        self.connector.settings["HOST"] = "hostname"
        self.connector.settings["ENGINE"] = "django.db.backends.postgresql"
        self.connector.settings["NAME"] = "dbname"

    def test_create_dump(self, mock_dump_cmd):
        dump = self.connector.create_dump()
        # Test dump
        dump_content = dump.read()
        assert dump_content
        assert dump_content == b"foo"
        # Test cmd
        assert mock_dump_cmd.called
        assert "--format=custom" in mock_dump_cmd.call_args[0][0]

    def test_create_dump_exclude(self, mock_dump_cmd):
        # Without
        self.connector.create_dump()
        assert " --exclude-table-data=" not in mock_dump_cmd.call_args[0][0]
        # With
        self.connector.exclude = ("foo",)
        self.connector.create_dump()
        assert " --exclude-table-data=foo" in mock_dump_cmd.call_args[0][0]
        # With several
        self.connector.exclude = ("foo", "bar")
        self.connector.create_dump()
        assert " --exclude-table-data=foo" in mock_dump_cmd.call_args[0][0]
        assert " --exclude-table-data=bar" in mock_dump_cmd.call_args[0][0]

    def test_create_dump_drop(self, mock_dump_cmd):
        # Without
        self.connector.drop = False
        self.connector.create_dump()
        assert " --clean" not in mock_dump_cmd.call_args[0][0]
        # Binary drop at restore level
        self.connector.drop = True
        self.connector.create_dump()
        assert " --clean" not in mock_dump_cmd.call_args[0][0]

    def test_create_dump_if_exists(self, mock_run_command):
        dump = self.connector.create_dump()

        # Default now includes --if-exists even without --clean
        self.connector.drop = False
        self.connector.restore_dump(dump)
        cmd_args = mock_run_command.call_args[0][0]
        assert " --clean" not in cmd_args
        assert " --if-exists" in cmd_args

        # Disabling if_exists explicitly should remove the flag (when drop=False)
        self.connector.if_exists = False
        self.connector.drop = False
        self.connector.restore_dump(dump)
        cmd_args = mock_run_command.call_args[0][0]
        assert " --clean" not in cmd_args
        assert " --if-exists" not in cmd_args

    def test_clean_automatically_enables_if_exists(self, mock_run_command):
        """Test that --if-exists is automatically added when using --clean to prevent identity column errors."""
        dump = self.connector.create_dump()

        # When drop=True (which adds --clean), --if-exists should be automatically added even if disabled
        self.connector.drop = True
        self.connector.if_exists = False  # Explicitly set to False
        self.connector.restore_dump(dump)
        cmd_args = mock_run_command.call_args[0][0]
        assert " --clean" in cmd_args
        assert " --if-exists" in cmd_args

        # When drop=False and if_exists=False, --if-exists should not be added
        self.connector.drop = False
        self.connector.if_exists = False
        self.connector.restore_dump(dump)
        cmd_args = mock_run_command.call_args[0][0]
        assert " --clean" not in cmd_args
        assert " --if-exists" not in cmd_args

    def test_pg_options(self, mock_run_command):
        dump = self.connector.create_dump()
        self.connector.pg_options = "--foo"
        self.connector.restore_dump(dump)
        cmd_args = mock_run_command.call_args[0][0]
        assert "--foo" in cmd_args

    def test_restore_prefix(self, mock_run_command):
        dump = self.connector.create_dump()
        self.connector.restore_prefix = "foo"
        self.connector.restore_dump(dump)
        cmd_args = mock_run_command.call_args[0][0]
        assert cmd_args.startswith("foo ")

    def test_restore_suffix(self, mock_run_command):
        dump = self.connector.create_dump()
        self.connector.restore_suffix = "foo"
        self.connector.restore_dump(dump)
        cmd_args = mock_run_command.call_args[0][0]
        assert cmd_args.endswith(" foo")

    @patch(
        "dbbackup.db.postgresql.PgDumpBinaryConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump(self, mock_dump_cmd, mock_restore_cmd):
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        # Test cmd
        assert mock_restore_cmd.called

    def test_create_dump_schema(self, mock_dump_cmd):
        # Without
        self.connector.create_dump()
        assert " -n " not in mock_dump_cmd.call_args[0][0]
        # With
        self.connector.schemas = ["public"]
        self.connector.create_dump()
        assert " -n public" in mock_dump_cmd.call_args[0][0]
        # With several
        self.connector.schemas = ["public", "foo"]
        self.connector.create_dump()
        assert " -n public" in mock_dump_cmd.call_args[0][0]
        assert " -n foo" in mock_dump_cmd.call_args[0][0]

    @patch(
        "dbbackup.db.postgresql.PgDumpBinaryConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump_schema(self, mock_dump_cmd, mock_restore_cmd):
        # Without
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        assert " -n " not in mock_restore_cmd.call_args[0][0]
        # With
        self.connector.schemas = ["public"]
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        assert " -n public" in mock_restore_cmd.call_args[0][0]
        # With several
        self.connector.schemas = ["public", "foo"]
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        assert " -n public" in mock_restore_cmd.call_args[0][0]
        assert " -n foo" in mock_restore_cmd.call_args[0][0]

    def test_create_dump_password_excluded(self, mock_dump_cmd):
        self.connector.settings["PASSWORD"] = "secret"
        self.connector.create_dump()
        assert "secret" not in mock_dump_cmd.call_args[0][0]

    def test_restore_dump_password_excluded(self, mock_dump_cmd):
        self.connector.settings["PASSWORD"] = "secret"
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        assert "secret" not in mock_dump_cmd.call_args[0][0]


@patch(
    "dbbackup.db.postgresql.PgDumpGisConnector.run_command",
    return_value=(BytesIO(b"foo"), BytesIO()),
)
class PgDumpGisConnectorTest(TestCase):
    def setUp(self):
        self.connector = PgDumpGisConnector()
        self.connector.settings["HOST"] = "hostname"

    @patch(
        "dbbackup.db.postgresql.PgDumpGisConnector.run_command",
        return_value=(BytesIO(b"foo"), BytesIO()),
    )
    def test_restore_dump(self, mock_dump_cmd, mock_restore_cmd):
        dump = self.connector.create_dump()
        # Without ADMINUSER
        self.connector.settings.pop("ADMIN_USER", None)
        self.connector.restore_dump(dump)
        assert mock_restore_cmd.called
        # With
        self.connector.settings["ADMIN_USER"] = "foo"
        self.connector.restore_dump(dump)
        assert mock_restore_cmd.called

    def test_enable_postgis(self, mock_dump_cmd):
        self.connector.settings["ADMIN_USER"] = "foo"
        self.connector._enable_postgis()
        assert '"CREATE EXTENSION IF NOT EXISTS postgis;"' in mock_dump_cmd.call_args[0][0]
        assert "--username=foo" in mock_dump_cmd.call_args[0][0]

    def test_enable_postgis_host(self, mock_dump_cmd):
        self.connector.settings["ADMIN_USER"] = "foo"
        # Without
        self.connector.settings.pop("HOST", None)
        self.connector._enable_postgis()
        assert " --host=" not in mock_dump_cmd.call_args[0][0]
        # With
        self.connector.settings["HOST"] = "foo"
        self.connector._enable_postgis()
        assert " --host=foo" in mock_dump_cmd.call_args[0][0]

    def test_enable_postgis_port(self, mock_dump_cmd):
        self.connector.settings["ADMIN_USER"] = "foo"
        # Without
        self.connector.settings.pop("PORT", None)
        self.connector._enable_postgis()
        assert " --port=" not in mock_dump_cmd.call_args[0][0]
        # With
        self.connector.settings["PORT"] = 42
        self.connector._enable_postgis()
        assert " --port=42" in mock_dump_cmd.call_args[0][0]

    def test_enable_postgis_special_characters(self, mock_dump_cmd):
        """Test that special characters in GIS connector parameters are properly escaped"""
        # Test admin user with special characters
        self.connector.settings["ADMIN_USER"] = "admin user"  # Space
        self.connector.settings["HOST"] = "localhost"
        self.connector._enable_postgis()
        command = mock_dump_cmd.call_args[0][0]
        assert "'admin user'" in command  # Should be quoted

        # Test host with special characters
        self.connector.settings["ADMIN_USER"] = "admin"
        self.connector.settings["HOST"] = "host@domain.com"  # @ symbol
        self.connector._enable_postgis()
        command = mock_dump_cmd.call_args[0][0]
        assert "host@domain.com" in command  # @ in hostname is safe, no quotes needed

        # Test admin user with quotes
        self.connector.settings["ADMIN_USER"] = "admin'user"  # Single quote
        self.connector.settings["HOST"] = "localhost"
        self.connector._enable_postgis()
        command = mock_dump_cmd.call_args[0][0]
        # Should escape the single quote properly
        assert "'admin'\"'\"'user'" in command


@patch(
    "dbbackup.db.base.Popen",
    **{
        "return_value.wait.return_value": True,
        "return_value.poll.return_value": False,
    },
)
class PgDumpConnectorRunCommandTest(TestCase):
    def test_run_command(self, mock_popen):
        connector = PgDumpConnector()
        connector.settings["HOST"] = "hostname"
        connector.create_dump()
        assert mock_popen.call_args[0][0][0] == "pg_dump"

    def test_run_command_with_password(self, mock_popen):
        connector = PgDumpConnector()
        connector.settings["HOST"] = "hostname"
        connector.settings["PASSWORD"] = "foo"
        connector.create_dump()
        assert mock_popen.call_args[0][0][0] == "pg_dump"
        assert "foo" not in " ".join(mock_popen.call_args[0][0])
        assert mock_popen.call_args[1]["env"]["PGPASSWORD"] == "foo"

    def test_run_command_with_password_and_other(self, mock_popen):
        connector = PgDumpConnector(env={"foo": "bar"})
        connector.settings["HOST"] = "hostname"
        connector.settings["PASSWORD"] = "foo"
        connector.create_dump()
        assert mock_popen.call_args[0][0][0] == "pg_dump"
        assert "foo" in mock_popen.call_args[1]["env"]
        assert mock_popen.call_args[1]["env"]["foo"] == "bar"
        assert "foo" not in " ".join(mock_popen.call_args[0][0])
        assert mock_popen.call_args[1]["env"]["PGPASSWORD"] == "foo"


class CreatePostgresDbNameAndEnvTest(TestCase):
    """Test the create_postgres_dbname_and_env helper function"""

    def test_function_with_normal_parameters(self):
        """Test function with normal parameters"""
        connector = Mock()
        connector.settings = {
            "HOST": "localhost",
            "PORT": 5432,
            "NAME": "testdb",
            "USER": "testuser",
            "PASSWORD": "testpass",
        }

        cmd_part, env = parse_postgres_settings(connector)

        assert cmd_part == "--dbname=postgresql://testuser@localhost:5432/testdb"
        assert env == {"PGPASSWORD": "testpass"}

    def test_function_with_special_characters(self):
        """Test function with special characters in user and password"""
        connector = Mock()
        connector.settings = {
            "HOST": "localhost",
            "PORT": 5432,
            "NAME": "testdb",
            "USER": "user@domain.com",  # Email-style username
            "PASSWORD": "my'pass\"word",  # Password with quotes
        }

        cmd_part, env = parse_postgres_settings(connector)

        # User should be URL-encoded in the connection string
        assert "user%40domain.com" in cmd_part
        # Password should be in environment variable unchanged
        assert env["PGPASSWORD"] == "my'pass\"word"
        # Password should not appear in URL
        assert "my'pass" not in cmd_part

    def test_function_without_user_or_password(self):
        """Test function without user or password"""
        connector = Mock()
        connector.settings = {"HOST": "localhost", "PORT": 5432, "NAME": "testdb"}

        cmd, env = parse_postgres_settings(connector)

        # No user means no @ in the URL
        assert cmd == "--dbname=postgresql://localhost:5432/testdb"
        # No password means empty environment
        assert env == {}

    def test_function_with_empty_password(self):
        """Test function with empty password"""
        connector = Mock()
        connector.settings = {
            "HOST": "localhost",
            "PORT": 5432,
            "NAME": "testdb",
            "USER": "testuser",
            "PASSWORD": "",  # Empty password
        }

        cmd_part, env = parse_postgres_settings(connector)

        assert "testuser@localhost" in cmd_part
        # Empty password should not create PGPASSWORD env var
        assert env == {}

        connector.settings = {
            "HOST": "localhost",
            "PORT": 5432,
            "NAME": "testdb",
            "USER": "testuser",
            "PASSWORD": None,  # "no password" case
        }

        cmd_part, env = parse_postgres_settings(connector)

        assert "testuser@localhost" in cmd_part
        # "None" password should not create PGPASSWORD env var, but should add --no-password flag
        assert env == {}
        assert "--no-password" in cmd_part
