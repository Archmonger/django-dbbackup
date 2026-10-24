from io import BytesIO
from pathlib import Path
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

    def test_create_dump_ssl_options(self, mock_dump_cmd):
        """Test the SSL options reach pg_dump through the environment, not the command line"""
        self.connector.settings["OPTIONS"] = {"sslmode": "verify-full", "sslcert": "/tmp/foo bar/cert.crt"}
        self.connector.create_dump()
        command = mock_dump_cmd.call_args[0][0]
        env = mock_dump_cmd.call_args[1]["env"]
        assert "?" not in command
        assert "sslmode" not in command
        assert "PGSSLMODE" not in command
        assert env["PGSSLMODE"] == "verify-full"
        assert env["PGSSLCERT"] == "/tmp/foo bar/cert.crt"

    def test_restore_dump_ssl_options(self, mock_dump_cmd):
        """Test the SSL options reach psql through the environment"""
        self.connector.settings["OPTIONS"] = {"sslmode": "verify-full", "sslrootcert": "/tmp/foo bar/ca.crt"}
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        command = mock_dump_cmd.call_args[0][0]
        env = mock_dump_cmd.call_args[1]["env"]
        assert "?" not in command
        assert env["PGSSLMODE"] == "verify-full"
        assert env["PGSSLROOTCERT"] == "/tmp/foo bar/ca.crt"

    def test_ssl_options_precedence_over_dump_env(self, mock_dump_cmd):
        """Test an option takes precedence over the same variable set in DUMP_ENV"""
        self.connector.dump_env = {"PGSSLMODE": "require"}
        self.connector.settings["OPTIONS"] = {"sslmode": "verify-full"}
        self.connector.create_dump()
        assert mock_dump_cmd.call_args[1]["env"]["PGSSLMODE"] == "verify-full"

    def test_dump_env_without_options(self, mock_dump_cmd):
        """Test DUMP_ENV keeps applying when no option is configured"""
        self.connector.dump_env = {"PGSSLMODE": "require"}
        self.connector.create_dump()
        assert mock_dump_cmd.call_args[1]["env"]["PGSSLMODE"] == "require"


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

    def test_restore_dump_quotes_unix_socket_host(self, mock_run_command):
        self.connector.settings["HOST"] = "/run/postgresql"
        self.connector.settings["PORT"] = 5432
        self.connector.settings["USER"] = "example"

        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)

        assert "--dbname=postgresql://example@%2Frun%2Fpostgresql:5432/dbname" in mock_run_command.call_args[0][0]

    def test_restore_dump_ssl_options(self, mock_run_command):
        """Test the SSL options reach pg_restore through the environment"""
        self.connector.settings["OPTIONS"] = {
            "sslmode": "verify-full",
            "sslcert": "C:\\Program Files\\pg\\cert.crt",
        }
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        command = mock_run_command.call_args[0][0]
        env = mock_run_command.call_args[1]["env"]
        assert "?" not in command
        assert "Program" not in command
        assert env["PGSSLMODE"] == "verify-full"
        assert env["PGSSLCERT"] == "C:\\Program Files\\pg\\cert.crt"

    def test_restore_dump_uses_restore_env(self, mock_run_command):
        """Test pg_restore gets RESTORE_ENV and not DUMP_ENV"""
        self.connector.dump_env = {"PGSSLMODE": "require", "FROM_DUMP": "yes"}
        self.connector.restore_env = {"PGSSLMODE": "disable", "FROM_RESTORE": "yes"}
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        env = mock_run_command.call_args[1]["env"]
        assert env["FROM_RESTORE"] == "yes"
        assert env["PGSSLMODE"] == "disable"
        assert "FROM_DUMP" not in env

    def test_create_dump_still_uses_dump_env(self, mock_run_command):
        """Test pg_dump keeps getting DUMP_ENV and not RESTORE_ENV"""
        self.connector.dump_env = {"FROM_DUMP": "yes"}
        self.connector.restore_env = {"FROM_RESTORE": "yes"}
        self.connector.create_dump()
        env = mock_run_command.call_args[1]["env"]
        assert env["FROM_DUMP"] == "yes"
        assert "FROM_RESTORE" not in env


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

    def test_enable_postgis_ssl_options(self, mock_dump_cmd):
        """Test the administrative connection uses the same TLS settings as the restore"""
        self.connector.settings["ADMIN_USER"] = "foo"
        self.connector.settings["OPTIONS"] = {
            "sslmode": "verify-full",
            "sslrootcert": "/tmp/foo bar/ca.crt",
            "sslcert": "C:\\Program Files\\pg\\admin.crt",
            "sslkey": "/tmp/foo bar/admin.key",
        }
        self.connector._enable_postgis()
        command = mock_dump_cmd.call_args[0][0]
        env = mock_dump_cmd.call_args[1]["env"]
        assert "?" not in command
        assert "verify-full" not in command
        assert env["PGSSLMODE"] == "verify-full"
        assert env["PGSSLROOTCERT"] == "/tmp/foo bar/ca.crt"
        assert env["PGSSLCERT"] == "C:\\Program Files\\pg\\admin.crt"
        assert env["PGSSLKEY"] == "/tmp/foo bar/admin.key"

    def test_enable_postgis_restore_env(self, mock_dump_cmd):
        """Test RESTORE_ENV applies to the administrative connection, options winning"""
        self.connector.settings["ADMIN_USER"] = "foo"
        self.connector.restore_env = {"PGSSLMODE": "require", "PGSSLCERT": "/tmp/restore.crt"}
        self.connector.settings["OPTIONS"] = {"sslcert": "/tmp/option.crt"}
        self.connector._enable_postgis()
        env = mock_dump_cmd.call_args[1]["env"]
        assert env["PGSSLMODE"] == "require"
        assert env["PGSSLCERT"] == "/tmp/option.crt"

    def test_enable_postgis_ignores_user_password(self, mock_dump_cmd):
        """Test the administrator connection does not reuse the database password"""
        self.connector.settings["ADMIN_USER"] = "foo"
        self.connector.settings["PASSWORD"] = "userpass"
        self.connector._enable_postgis()
        command = mock_dump_cmd.call_args[0][0]
        env = mock_dump_cmd.call_args[1]["env"]
        assert "userpass" not in command
        assert "PGPASSWORD" not in env
        assert "--no-password" in command

    def test_enable_postgis_admin_password(self, mock_dump_cmd):
        """Test ADMIN_PASSWORD is used for the administrative connection"""
        self.connector.settings["ADMIN_USER"] = "foo"
        self.connector.settings["ADMIN_PASSWORD"] = "secret"
        self.connector._enable_postgis()
        command = mock_dump_cmd.call_args[0][0]
        env = mock_dump_cmd.call_args[1]["env"]
        assert "secret" not in command
        assert env["PGPASSWORD"] == "secret"
        assert "--no-password" in command


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
    """Test the parse_postgres_settings helper function"""

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

    def test_function_url_quotes_unix_socket_host(self):
        """Test function URL-quotes unix socket hosts in the connection string"""
        connector = Mock()
        connector.settings = {
            "HOST": "/run/postgresql",
            "PORT": 5432,
            "NAME": "inventree",
            "USER": "inventree",
        }

        cmd_part, env = parse_postgres_settings(connector)

        assert cmd_part == "--dbname=postgresql://inventree@%2Frun%2Fpostgresql:5432/inventree"
        assert env == {}

    def test_function_preserves_ipv6_host(self):
        """Test function preserves valid IPv6 host syntax in the URI hostspec"""
        connector = Mock()
        connector.settings = {
            "HOST": "[2001:db8::1234]",
            "PORT": 5432,
            "NAME": "testdb",
            "USER": "testuser",
        }

        cmd_part, env = parse_postgres_settings(connector)

        assert cmd_part == "--dbname=postgresql://testuser@[2001:db8::1234]:5432/testdb"
        assert env == {}

    def test_function_defaults_none_host_to_localhost(self):
        """Test function defaults an unset HOST value to localhost"""
        connector = Mock()
        connector.settings = {"HOST": None, "PORT": 5432, "NAME": "testdb"}

        cmd_part, env = parse_postgres_settings(connector)

        assert cmd_part == "--dbname=postgresql://localhost:5432/testdb"
        assert env == {}

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

    def test_function_with_client_certificate_authentication(self):
        """Test client certificate authentication is passed through the environment"""
        connector = Mock()
        connector.settings = {
            "HOST": "localhost",
            "PORT": 5432,
            "NAME": "testdb",
            "USER": "testuser",
            "PASSWORD": "",
            "OPTIONS": {
                "sslcert": "/tmp/foo/bar/cert.crt",
                "sslkey": "/tmp/foo/bar/cert.key",
                "sslrootcert": "/tmp/foo/bar/ca.crt",
                "sslmode": "verify-full",
            },
        }

        cmd_part, env = parse_postgres_settings(connector)

        # No query string: libpq expands "%XX" triplets only, anything else
        # would reach the command line tools corrupted.
        assert cmd_part == "--dbname=postgresql://testuser@localhost:5432/testdb"
        assert env == {
            "PGSSLMODE": "verify-full",
            "PGSSLROOTCERT": "/tmp/foo/bar/ca.crt",
            "PGSSLCERT": "/tmp/foo/bar/cert.crt",
            "PGSSLKEY": "/tmp/foo/bar/cert.key",
        }

    def test_function_with_paths_needing_no_encoding(self):
        """Test certificate paths are transmitted verbatim, whatever they contain"""
        connector = Mock()
        connector.settings = {
            "HOST": "localhost",
            "PORT": 5432,
            "NAME": "testdb",
            "USER": "testuser",
            "OPTIONS": {
                "sslcert": "C:\\Program Files\\pg\\cert.crt",
                "sslkey": "/home/user/my certs/client.key",
                "sslrootcert": "/home/user/100% sure/ca.pem",
                "sslmode": "verify-full",
            },
        }

        cmd_part, env = parse_postgres_settings(connector)

        assert "?" not in cmd_part
        assert env == {
            "PGSSLMODE": "verify-full",
            "PGSSLROOTCERT": "/home/user/100% sure/ca.pem",
            "PGSSLCERT": "C:\\Program Files\\pg\\cert.crt",
            "PGSSLKEY": "/home/user/my certs/client.key",
        }

    def test_function_with_pathlib_option_values(self):
        """Test pathlib values are accepted and stringified"""
        connector = Mock()
        connector.settings = {
            "HOST": "localhost",
            "NAME": "testdb",
            "USER": "testuser",
            "OPTIONS": {
                "sslcert": Path("/tmp/foo bar/cert.crt"),
                "sslrootcert": Path("/tmp/foo bar/ca.crt"),
            },
        }

        _cmd_part, env = parse_postgres_settings(connector)

        assert env == {
            "PGSSLROOTCERT": "/tmp/foo bar/ca.crt",
            "PGSSLCERT": "/tmp/foo bar/cert.crt",
        }

    def test_function_with_password_file_and_service(self):
        """Test the other options Django forwards to its own command line tools"""
        connector = Mock()
        connector.settings = {
            "HOST": "localhost",
            "PORT": 5432,
            "NAME": "testdb",
            "USER": "testuser",
            "OPTIONS": {
                "passfile": "/home/user/.pgpass",
                "service": "my_service",
            },
        }

        cmd_part, env = parse_postgres_settings(connector)

        assert cmd_part == "--dbname=postgresql://testuser@localhost:5432/testdb"
        assert env == {"PGPASSFILE": "/home/user/.pgpass", "PGSERVICE": "my_service"}

    def test_function_with_partial_ssl_options(self):
        """Test a single option is forwarded on its own, and empty values are ignored"""
        connector = Mock()
        connector.settings = {
            "HOST": "localhost",
            "PORT": 5432,
            "NAME": "testdb",
            "USER": "testuser",
            "OPTIONS": {"sslmode": "require"},
        }

        cmd_part, env = parse_postgres_settings(connector)

        assert cmd_part == "--dbname=postgresql://testuser@localhost:5432/testdb"
        assert env == {"PGSSLMODE": "require"}

        connector.settings["OPTIONS"] = {"sslmode": "require", "sslcert": "", "sslkey": None}

        _cmd_part, env = parse_postgres_settings(connector)

        assert env == {"PGSSLMODE": "require"}

    def test_function_ignores_unsupported_options(self):
        """Test options which do not affect the command line tools are not forwarded"""
        connector = Mock()
        connector.settings = {
            "HOST": "localhost",
            "PORT": 5432,
            "NAME": "testdb",
            "USER": "testuser",
            "OPTIONS": {
                "application_name": "dbbackup",
                "connect_timeout": 10,
                "options": "-c statement_timeout=0",
                "ssl": True,
            },
        }

        _cmd_part, env = parse_postgres_settings(connector)

        assert env == {}

    def test_function_without_options(self):
        """Test a missing or unset OPTIONS setting produces no extra environment"""
        connector = Mock()
        connector.settings = {
            "HOST": "localhost",
            "PORT": 5432,
            "NAME": "testdb",
            "USER": "testuser",
        }

        _cmd_part, env = parse_postgres_settings(connector)

        assert env == {}

        connector.settings["OPTIONS"] = None

        _cmd_part, env = parse_postgres_settings(connector)

        assert env == {}

    def test_function_keeps_password_with_ssl_options(self):
        """Test the password and the options end up together in the environment"""
        connector = Mock()
        connector.settings = {
            "HOST": "localhost",
            "PORT": 5432,
            "NAME": "testdb",
            "USER": "testuser",
            "PASSWORD": "testpass",
            "OPTIONS": {"sslmode": "verify-full", "sslrootcert": "/tmp/foo/bar/ca.crt"},
        }

        cmd_part, env = parse_postgres_settings(connector)

        assert cmd_part == "--dbname=postgresql://testuser@localhost:5432/testdb"
        assert env == {
            "PGPASSWORD": "testpass",
            "PGSSLMODE": "verify-full",
            "PGSSLROOTCERT": "/tmp/foo/bar/ca.crt",
        }
