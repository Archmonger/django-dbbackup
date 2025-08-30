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
        assert dump_content
        assert dump_content == b"foo"
        # Test cmd
        assert mock_dump_cmd.called

    def test_create_dump_host(self, mock_dump_cmd):
        connector = MysqlDumpConnector()
        # Without
        connector.settings.pop("HOST", None)
        connector.create_dump()
        assert " --host=" not in mock_dump_cmd.call_args[0][0]
        # With
        connector.settings["HOST"] = "foo"
        connector.create_dump()
        assert " --host=foo" in mock_dump_cmd.call_args[0][0]

    def test_create_dump_port(self, mock_dump_cmd):
        connector = MysqlDumpConnector()
        # Without
        connector.settings.pop("PORT", None)
        connector.create_dump()
        assert " --port=" not in mock_dump_cmd.call_args[0][0]
        # With
        connector.settings["PORT"] = 42
        connector.create_dump()
        assert " --port=42" in mock_dump_cmd.call_args[0][0]

    def test_create_dump_user(self, mock_dump_cmd):
        connector = MysqlDumpConnector()
        # Without
        connector.settings.pop("USER", None)
        connector.create_dump()
        assert " --user=" not in mock_dump_cmd.call_args[0][0]
        # With
        connector.settings["USER"] = "foo"
        connector.create_dump()
        assert " --user=foo" in mock_dump_cmd.call_args[0][0]

    def test_create_dump_password(self, mock_dump_cmd):
        connector = MysqlDumpConnector()
        # Without
        connector.settings.pop("PASSWORD", None)
        connector.create_dump()
        assert " --password=" not in mock_dump_cmd.call_args[0][0]
        # With
        connector.settings["PASSWORD"] = "foo"
        connector.create_dump()
        assert " --password=foo" in mock_dump_cmd.call_args[0][0]

    def test_create_dump_password_with_special_chars(self, mock_dump_cmd):
        connector = MysqlDumpConnector()

        # Test password with spaces
        connector.settings["PASSWORD"] = "password with spaces"
        connector.create_dump()
        cmd = mock_dump_cmd.call_args[0][0]
        # Should be properly escaped with quotes
        assert " --password='password with spaces'" in cmd

        # Test password with special characters that could break shells
        connector.settings["PASSWORD"] = "pass!@#$%^&*()"
        connector.create_dump()
        cmd = mock_dump_cmd.call_args[0][0]
        # Should be properly escaped - exact format depends on shlex.quote()
        assert " --password='pass!@#$%^&*()'" in cmd

        # Test password with quotes - this is the trickiest case
        connector.settings["PASSWORD"] = "pass'word\"test"
        connector.create_dump()
        cmd = mock_dump_cmd.call_args[0][0]
        # Should be properly escaped
        assert " --password='pass'\"'\"'word\"test'" in cmd

    def test_create_dump_exclude(self, mock_dump_cmd):
        connector = MysqlDumpConnector()
        connector.settings["NAME"] = "db"
        # Without
        connector.create_dump()
        assert " --ignore-table=" not in mock_dump_cmd.call_args[0][0]
        # With
        connector.exclude = ("foo",)
        connector.create_dump()
        assert " --ignore-table=db.foo" in mock_dump_cmd.call_args[0][0]
        # With several
        connector.exclude = ("foo", "bar")
        connector.create_dump()
        assert " --ignore-table=db.foo" in mock_dump_cmd.call_args[0][0]
        assert " --ignore-table=db.bar" in mock_dump_cmd.call_args[0][0]

    @patch(
        "dbbackup.db.mysql.MysqlDumpConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump(self, mock_dump_cmd, mock_restore_cmd):
        connector = MysqlDumpConnector()
        dump = connector.create_dump()
        connector.restore_dump(dump)
        # Test cmd
        assert mock_restore_cmd.called

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
        assert " --host=foo" not in mock_restore_cmd.call_args[0][0]
        # With
        connector.settings["HOST"] = "foo"
        connector.restore_dump(dump)
        assert " --host=foo" in mock_restore_cmd.call_args[0][0]

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
        assert " --port=" not in mock_restore_cmd.call_args[0][0]
        # With
        connector.settings["PORT"] = 42
        connector.restore_dump(dump)
        assert " --port=42" in mock_restore_cmd.call_args[0][0]

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
        assert " --user=" not in mock_restore_cmd.call_args[0][0]
        # With
        connector.settings["USER"] = "foo"
        connector.restore_dump(dump)
        assert " --user=foo" in mock_restore_cmd.call_args[0][0]

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
        assert " --password=" not in mock_restore_cmd.call_args[0][0]
        # With
        connector.settings["PASSWORD"] = "foo"
        connector.restore_dump(dump)
        assert " --password=foo" in mock_restore_cmd.call_args[0][0]

    @patch(
        "dbbackup.db.mysql.MysqlDumpConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump_password_with_special_chars(self, mock_dump_cmd, mock_restore_cmd):
        connector = MysqlDumpConnector()
        dump = connector.create_dump()

        # Test password with spaces
        connector.settings["PASSWORD"] = "password with spaces"
        connector.restore_dump(dump)
        cmd = mock_restore_cmd.call_args[0][0]
        assert " --password='password with spaces'" in cmd

        # Test password with special characters
        connector.settings["PASSWORD"] = "pass!@#$%^&*()"
        connector.restore_dump(dump)
        cmd = mock_restore_cmd.call_args[0][0]
        # Should be properly escaped
        assert " --password='pass!@#$%^&*()'" in cmd

        # Test password with quotes
        connector.settings["PASSWORD"] = "pass'word\"test"
        connector.restore_dump(dump)
        cmd = mock_restore_cmd.call_args[0][0]
        # Should be properly escaped
        assert " --password='pass'\"'\"'word\"test'" in cmd
