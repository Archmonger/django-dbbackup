from io import BytesIO
from unittest.mock import patch

from django.test import TestCase

from dbbackup.db.mysql import MysqlDumpConnector


@patch(
    "dbbackup.db.mysql.MysqlDumpConnector.run_command",
    return_value=(BytesIO(b"foo"), BytesIO()),
)
class MysqlDumpConnectorTest(TestCase):
    def test_create_dump(self, mock_dump_cmd):
        connector = MysqlDumpConnector()
        dump = connector.create_dump()
        # Test dump
        dump_content = dump.read()
        self.assertTrue(dump_content)
        self.assertEqual(dump_content, b"foo")
        # Test cmd
        self.assertTrue(mock_dump_cmd.called)

    def test_create_dump_host(self, mock_dump_cmd):
        connector = MysqlDumpConnector()
        # Without
        connector.settings.pop("HOST", None)
        connector.create_dump()
        self.assertNotIn(" --host=", mock_dump_cmd.call_args[0][0])
        # With
        connector.settings["HOST"] = "foo"
        connector.create_dump()
        self.assertIn(" --host=foo", mock_dump_cmd.call_args[0][0])

    def test_create_dump_port(self, mock_dump_cmd):
        connector = MysqlDumpConnector()
        # Without
        connector.settings.pop("PORT", None)
        connector.create_dump()
        self.assertNotIn(" --port=", mock_dump_cmd.call_args[0][0])
        # With
        connector.settings["PORT"] = 42
        connector.create_dump()
        self.assertIn(" --port=42", mock_dump_cmd.call_args[0][0])

    def test_create_dump_user(self, mock_dump_cmd):
        connector = MysqlDumpConnector()
        # Without
        connector.settings.pop("USER", None)
        connector.create_dump()
        self.assertNotIn(" --user=", mock_dump_cmd.call_args[0][0])
        # With
        connector.settings["USER"] = "foo"
        connector.create_dump()
        self.assertIn(" --user=foo", mock_dump_cmd.call_args[0][0])

    def test_create_dump_password(self, mock_dump_cmd):
        connector = MysqlDumpConnector()
        # Without
        connector.settings.pop("PASSWORD", None)
        connector.create_dump()
        self.assertNotIn(" --password=", mock_dump_cmd.call_args[0][0])
        # With
        connector.settings["PASSWORD"] = "foo"
        connector.create_dump()
        self.assertIn(" --password=foo", mock_dump_cmd.call_args[0][0])

    def test_create_dump_exclude(self, mock_dump_cmd):
        connector = MysqlDumpConnector()
        connector.settings["NAME"] = "db"
        # Without
        connector.create_dump()
        self.assertNotIn(" --ignore-table=", mock_dump_cmd.call_args[0][0])
        # With
        connector.exclude = ("foo",)
        connector.create_dump()
        self.assertIn(" --ignore-table=db.foo", mock_dump_cmd.call_args[0][0])
        # With several
        connector.exclude = ("foo", "bar")
        connector.create_dump()
        self.assertIn(" --ignore-table=db.foo", mock_dump_cmd.call_args[0][0])
        self.assertIn(" --ignore-table=db.bar", mock_dump_cmd.call_args[0][0])

    @patch(
        "dbbackup.db.mysql.MysqlDumpConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump(self, mock_dump_cmd, mock_restore_cmd):
        connector = MysqlDumpConnector()
        dump = connector.create_dump()
        connector.restore_dump(dump)
        # Test cmd
        self.assertTrue(mock_restore_cmd.called)

    @patch(
        "dbbackup.db.mysql.MysqlDumpConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump_host(self, mock_dump_cmd, mock_restore_cmd):
        connector = MysqlDumpConnector()
        dump = connector.create_dump()
        # Without
        connector.settings.pop("HOST", None)
        connector.restore_dump(dump)
        self.assertNotIn(" --host=foo", mock_restore_cmd.call_args[0][0])
        # With
        connector.settings["HOST"] = "foo"
        connector.restore_dump(dump)
        self.assertIn(" --host=foo", mock_restore_cmd.call_args[0][0])

    @patch(
        "dbbackup.db.mysql.MysqlDumpConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump_port(self, mock_dump_cmd, mock_restore_cmd):
        connector = MysqlDumpConnector()
        dump = connector.create_dump()
        # Without
        connector.settings.pop("PORT", None)
        connector.restore_dump(dump)
        self.assertNotIn(" --port=", mock_restore_cmd.call_args[0][0])
        # With
        connector.settings["PORT"] = 42
        connector.restore_dump(dump)
        self.assertIn(" --port=42", mock_restore_cmd.call_args[0][0])

    @patch(
        "dbbackup.db.mysql.MysqlDumpConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump_user(self, mock_dump_cmd, mock_restore_cmd):
        connector = MysqlDumpConnector()
        dump = connector.create_dump()
        # Without
        connector.settings.pop("USER", None)
        connector.restore_dump(dump)
        self.assertNotIn(" --user=", mock_restore_cmd.call_args[0][0])
        # With
        connector.settings["USER"] = "foo"
        connector.restore_dump(dump)
        self.assertIn(" --user=foo", mock_restore_cmd.call_args[0][0])

    @patch(
        "dbbackup.db.mysql.MysqlDumpConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump_password(self, mock_dump_cmd, mock_restore_cmd):
        connector = MysqlDumpConnector()
        dump = connector.create_dump()
        # Without
        connector.settings.pop("PASSWORD", None)
        connector.restore_dump(dump)
        self.assertNotIn(" --password=", mock_restore_cmd.call_args[0][0])
        # With
        connector.settings["PASSWORD"] = "foo"
        connector.restore_dump(dump)
        self.assertIn(" --password=foo", mock_restore_cmd.call_args[0][0])
