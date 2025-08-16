from io import BytesIO
from unittest.mock import patch

from django.test import TestCase

from dbbackup.db.postgresql import (
    PgDumpBinaryConnector,
    PgDumpConnector,
    PgDumpGisConnector,
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
        self.assertIn("postgresql://%40@hostname/dbname", mock_dump_cmd.call_args[0][0])

    def test_create_dump(self, mock_dump_cmd):
        dump = self.connector.create_dump()
        # Test dump
        dump_content = dump.read()
        self.assertTrue(dump_content)
        self.assertEqual(dump_content, b"foo")
        # Test cmd
        self.assertTrue(mock_dump_cmd.called)

    def test_create_dump_without_host(self, mock_dump_cmd):
        # this is allowed now: https://github.com/Archmonger/django-dbbackup/issues/520
        self.connector.settings.pop("HOST", None)
        self.connector.create_dump()

    def test_password_but_no_user(self, mock_dump_cmd):
        self.connector.settings.pop("USER", None)
        self.connector.settings["PASSWORD"] = "hello"
        self.connector.create_dump()
        self.assertIn("postgresql://hostname/dbname", mock_dump_cmd.call_args[0][0])

    def test_create_dump_host(self, mock_dump_cmd):
        # With
        self.connector.settings["HOST"] = "foo"
        self.connector.create_dump()
        self.assertIn("postgresql://foo/dbname", mock_dump_cmd.call_args[0][0])

    def test_create_dump_port(self, mock_dump_cmd):
        # Without
        self.connector.settings.pop("PORT", None)
        self.connector.create_dump()
        self.assertIn("postgresql://hostname/dbname", mock_dump_cmd.call_args[0][0])
        # With
        self.connector.settings["PORT"] = 42
        self.connector.create_dump()
        self.assertIn("postgresql://hostname:42/dbname", mock_dump_cmd.call_args[0][0])

    def test_create_dump_user(self, mock_dump_cmd):
        # Without
        self.connector.settings.pop("USER", None)
        self.connector.create_dump()
        self.assertIn("postgresql://hostname/dbname", mock_dump_cmd.call_args[0][0])
        # With
        self.connector.settings["USER"] = "foo"
        self.connector.create_dump()
        self.assertIn("postgresql://foo@hostname/dbname", mock_dump_cmd.call_args[0][0])

    def test_create_dump_exclude(self, mock_dump_cmd):
        # Without
        self.connector.create_dump()
        self.assertNotIn(" --exclude-table-data=", mock_dump_cmd.call_args[0][0])
        # With
        self.connector.exclude = ("foo",)
        self.connector.create_dump()
        self.assertIn(" --exclude-table-data=foo", mock_dump_cmd.call_args[0][0])
        # With several
        self.connector.exclude = ("foo", "bar")
        self.connector.create_dump()
        self.assertIn(" --exclude-table-data=foo", mock_dump_cmd.call_args[0][0])
        self.assertIn(" --exclude-table-data=bar", mock_dump_cmd.call_args[0][0])

    def test_create_dump_drop(self, mock_dump_cmd):
        # Without
        self.connector.drop = False
        self.connector.create_dump()
        self.assertNotIn(" --clean", mock_dump_cmd.call_args[0][0])
        # With
        self.connector.drop = True
        self.connector.create_dump()
        self.assertIn(" --clean", mock_dump_cmd.call_args[0][0])

    @patch(
        "dbbackup.db.postgresql.PgDumpConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump(self, mock_dump_cmd, mock_restore_cmd):
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        # Test cmd
        self.assertTrue(mock_restore_cmd.called)

    @patch(
        "dbbackup.db.postgresql.PgDumpConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump_user(self, mock_dump_cmd, mock_restore_cmd):
        dump = self.connector.create_dump()
        # Without
        self.connector.settings.pop("USER", None)
        self.connector.restore_dump(dump)

        self.assertIn("postgresql://hostname/dbname", mock_restore_cmd.call_args[0][0])

        self.assertNotIn(" --username=", mock_restore_cmd.call_args[0][0])
        # With
        self.connector.settings["USER"] = "foo"
        self.connector.restore_dump(dump)
        self.assertIn(
            "postgresql://foo@hostname/dbname", mock_restore_cmd.call_args[0][0]
        )

    def test_create_dump_schema(self, mock_dump_cmd):
        # Without
        self.connector.create_dump()
        self.assertNotIn(" -n ", mock_dump_cmd.call_args[0][0])
        # With
        self.connector.schemas = ["public"]
        self.connector.create_dump()
        self.assertIn(" -n public", mock_dump_cmd.call_args[0][0])
        # With several
        self.connector.schemas = ["public", "foo"]
        self.connector.create_dump()
        self.assertIn(" -n public", mock_dump_cmd.call_args[0][0])
        self.assertIn(" -n foo", mock_dump_cmd.call_args[0][0])

    @patch(
        "dbbackup.db.postgresql.PgDumpConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump_schema(self, mock_dump_cmd, mock_restore_cmd):
        # Without
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        self.assertNotIn(" -n ", mock_restore_cmd.call_args[0][0])
        # With
        self.connector.schemas = ["public"]
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        self.assertIn(" -n public", mock_restore_cmd.call_args[0][0])
        # With several
        self.connector.schemas = ["public", "foo"]
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        self.assertIn(" -n public", mock_restore_cmd.call_args[0][0])
        self.assertIn(" -n foo", mock_restore_cmd.call_args[0][0])

    def test_create_dump_password_excluded(self, mock_dump_cmd):
        self.connector.settings["PASSWORD"] = "secret"
        self.connector.create_dump()
        self.assertNotIn("secret", mock_dump_cmd.call_args[0][0])

    def test_restore_dump_password_excluded(self, mock_dump_cmd):
        self.connector.settings["PASSWORD"] = "secret"
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        self.assertNotIn("secret", mock_dump_cmd.call_args[0][0])


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
        self.assertTrue(dump_content)
        self.assertEqual(dump_content, b"foo")
        # Test cmd
        self.assertTrue(mock_dump_cmd.called)
        self.assertIn("--format=custom", mock_dump_cmd.call_args[0][0])

    def test_create_dump_exclude(self, mock_dump_cmd):
        # Without
        self.connector.create_dump()
        self.assertNotIn(" --exclude-table-data=", mock_dump_cmd.call_args[0][0])
        # With
        self.connector.exclude = ("foo",)
        self.connector.create_dump()
        self.assertIn(" --exclude-table-data=foo", mock_dump_cmd.call_args[0][0])
        # With several
        self.connector.exclude = ("foo", "bar")
        self.connector.create_dump()
        self.assertIn(" --exclude-table-data=foo", mock_dump_cmd.call_args[0][0])
        self.assertIn(" --exclude-table-data=bar", mock_dump_cmd.call_args[0][0])

    def test_create_dump_drop(self, mock_dump_cmd):
        # Without
        self.connector.drop = False
        self.connector.create_dump()
        self.assertNotIn(" --clean", mock_dump_cmd.call_args[0][0])
        # Binary drop at restore level
        self.connector.drop = True
        self.connector.create_dump()
        self.assertNotIn(" --clean", mock_dump_cmd.call_args[0][0])

    def test_create_dump_if_exists(self, mock_run_command):
        dump = self.connector.create_dump()
        # Without
        self.connector.if_exists = False
        self.connector.restore_dump(dump)
        self.assertNotIn(" --if-exists", mock_run_command.call_args[0][0])
        # With
        self.connector.if_exists = True
        self.connector.restore_dump(dump)
        self.assertIn(" --if-exists", mock_run_command.call_args[0][0])

    def test_pg_options(self, mock_run_command):
        dump = self.connector.create_dump()
        self.connector.pg_options = "--foo"
        self.connector.restore_dump(dump)
        cmd_args = mock_run_command.call_args[0][0]
        self.assertIn("--foo", cmd_args)

    def test_restore_prefix(self, mock_run_command):
        dump = self.connector.create_dump()
        self.connector.restore_prefix = "foo"
        self.connector.restore_dump(dump)
        cmd_args = mock_run_command.call_args[0][0]
        self.assertTrue(cmd_args.startswith("foo "))

    def test_restore_suffix(self, mock_run_command):
        dump = self.connector.create_dump()
        self.connector.restore_suffix = "foo"
        self.connector.restore_dump(dump)
        cmd_args = mock_run_command.call_args[0][0]
        self.assertTrue(cmd_args.endswith(" foo"))

    @patch(
        "dbbackup.db.postgresql.PgDumpBinaryConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump(self, mock_dump_cmd, mock_restore_cmd):
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        # Test cmd
        self.assertTrue(mock_restore_cmd.called)

    def test_create_dump_schema(self, mock_dump_cmd):
        # Without
        self.connector.create_dump()
        self.assertNotIn(" -n ", mock_dump_cmd.call_args[0][0])
        # With
        self.connector.schemas = ["public"]
        self.connector.create_dump()
        self.assertIn(" -n public", mock_dump_cmd.call_args[0][0])
        # With several
        self.connector.schemas = ["public", "foo"]
        self.connector.create_dump()
        self.assertIn(" -n public", mock_dump_cmd.call_args[0][0])
        self.assertIn(" -n foo", mock_dump_cmd.call_args[0][0])

    @patch(
        "dbbackup.db.postgresql.PgDumpBinaryConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump_schema(self, mock_dump_cmd, mock_restore_cmd):
        # Without
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        self.assertNotIn(" -n ", mock_restore_cmd.call_args[0][0])
        # With
        self.connector.schemas = ["public"]
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        self.assertIn(" -n public", mock_restore_cmd.call_args[0][0])
        # With several
        self.connector.schemas = ["public", "foo"]
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        self.assertIn(" -n public", mock_restore_cmd.call_args[0][0])
        self.assertIn(" -n foo", mock_restore_cmd.call_args[0][0])

    def test_create_dump_password_excluded(self, mock_dump_cmd):
        self.connector.settings["PASSWORD"] = "secret"
        self.connector.create_dump()
        self.assertNotIn("secret", mock_dump_cmd.call_args[0][0])

    def test_restore_dump_password_excluded(self, mock_dump_cmd):
        self.connector.settings["PASSWORD"] = "secret"
        dump = self.connector.create_dump()
        self.connector.restore_dump(dump)
        self.assertNotIn("secret", mock_dump_cmd.call_args[0][0])


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
        self.assertTrue(mock_restore_cmd.called)
        # With
        self.connector.settings["ADMIN_USER"] = "foo"
        self.connector.restore_dump(dump)
        self.assertTrue(mock_restore_cmd.called)

    def test_enable_postgis(self, mock_dump_cmd):
        self.connector.settings["ADMIN_USER"] = "foo"
        self.connector._enable_postgis()
        self.assertIn(
            '"CREATE EXTENSION IF NOT EXISTS postgis;"', mock_dump_cmd.call_args[0][0]
        )
        self.assertIn("--username=foo", mock_dump_cmd.call_args[0][0])

    def test_enable_postgis_host(self, mock_dump_cmd):
        self.connector.settings["ADMIN_USER"] = "foo"
        # Without
        self.connector.settings.pop("HOST", None)
        self.connector._enable_postgis()
        self.assertNotIn(" --host=", mock_dump_cmd.call_args[0][0])
        # With
        self.connector.settings["HOST"] = "foo"
        self.connector._enable_postgis()
        self.assertIn(" --host=foo", mock_dump_cmd.call_args[0][0])

    def test_enable_postgis_port(self, mock_dump_cmd):
        self.connector.settings["ADMIN_USER"] = "foo"
        # Without
        self.connector.settings.pop("PORT", None)
        self.connector._enable_postgis()
        self.assertNotIn(" --port=", mock_dump_cmd.call_args[0][0])
        # With
        self.connector.settings["PORT"] = 42
        self.connector._enable_postgis()
        self.assertIn(" --port=42", mock_dump_cmd.call_args[0][0])


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
        self.assertEqual(mock_popen.call_args[0][0][0], "pg_dump")

    def test_run_command_with_password(self, mock_popen):
        connector = PgDumpConnector()
        connector.settings["HOST"] = "hostname"
        connector.settings["PASSWORD"] = "foo"
        connector.create_dump()
        self.assertEqual(mock_popen.call_args[0][0][0], "pg_dump")
        self.assertNotIn("foo", " ".join(mock_popen.call_args[0][0]))
        self.assertEqual("foo", mock_popen.call_args[1]["env"]["PGPASSWORD"])

    def test_run_command_with_password_and_other(self, mock_popen):
        connector = PgDumpConnector(env={"foo": "bar"})
        connector.settings["HOST"] = "hostname"
        connector.settings["PASSWORD"] = "foo"
        connector.create_dump()
        self.assertEqual(mock_popen.call_args[0][0][0], "pg_dump")
        self.assertIn("foo", mock_popen.call_args[1]["env"])
        self.assertEqual("bar", mock_popen.call_args[1]["env"]["foo"])
        self.assertNotIn("foo", " ".join(mock_popen.call_args[0][0]))
        self.assertEqual("foo", mock_popen.call_args[1]["env"]["PGPASSWORD"])
