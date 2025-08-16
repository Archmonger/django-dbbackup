from io import BytesIO
from unittest.mock import patch

from django.test import TestCase

from dbbackup.db.mongodb import MongoDumpConnector


@patch(
    "dbbackup.db.mongodb.MongoDumpConnector.run_command",
    return_value=(BytesIO(b"foo"), BytesIO()),
)
class MongoDumpConnectorTest(TestCase):
    def test_create_dump(self, mock_dump_cmd):
        connector = MongoDumpConnector()
        dump = connector.create_dump()
        # Test dump
        dump_content = dump.read()
        self.assertTrue(dump_content)
        self.assertEqual(dump_content, b"foo")
        # Test cmd
        self.assertTrue(mock_dump_cmd.called)

    def test_create_dump_user(self, mock_dump_cmd):
        connector = MongoDumpConnector()
        # Without
        connector.settings.pop("USER", None)
        connector.create_dump()
        self.assertNotIn(" --user ", mock_dump_cmd.call_args[0][0])
        # With
        connector.settings["USER"] = "foo"
        connector.create_dump()
        self.assertIn(" --username foo", mock_dump_cmd.call_args[0][0])

    def test_create_dump_password(self, mock_dump_cmd):
        connector = MongoDumpConnector()
        # Without
        connector.settings.pop("PASSWORD", None)
        connector.create_dump()
        self.assertNotIn(" --password ", mock_dump_cmd.call_args[0][0])
        # With
        connector.settings["PASSWORD"] = "foo"
        connector.create_dump()
        self.assertIn(" --password foo", mock_dump_cmd.call_args[0][0])

    @patch(
        "dbbackup.db.mongodb.MongoDumpConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump(self, mock_dump_cmd, mock_restore_cmd):
        connector = MongoDumpConnector()
        dump = connector.create_dump()
        connector.restore_dump(dump)
        # Test cmd
        self.assertTrue(mock_restore_cmd.called)

    @patch(
        "dbbackup.db.mongodb.MongoDumpConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump_user(self, mock_dump_cmd, mock_restore_cmd):
        connector = MongoDumpConnector()
        dump = connector.create_dump()
        # Without
        connector.settings.pop("USER", None)
        connector.restore_dump(dump)
        self.assertNotIn(" --username ", mock_restore_cmd.call_args[0][0])
        # With
        connector.settings["USER"] = "foo"
        connector.restore_dump(dump)
        self.assertIn(" --username foo", mock_restore_cmd.call_args[0][0])

    @patch(
        "dbbackup.db.mongodb.MongoDumpConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump_password(self, mock_dump_cmd, mock_restore_cmd):
        connector = MongoDumpConnector()
        dump = connector.create_dump()
        # Without
        connector.settings.pop("PASSWORD", None)
        connector.restore_dump(dump)
        self.assertNotIn(" --password ", mock_restore_cmd.call_args[0][0])
        # With
        connector.settings["PASSWORD"] = "foo"
        connector.restore_dump(dump)
        self.assertIn(" --password foo", mock_restore_cmd.call_args[0][0])

    @patch(
        "dbbackup.db.mongodb.MongoDumpConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump_object_check(self, mock_dump_cmd, mock_restore_cmd):
        connector = MongoDumpConnector()
        dump = connector.create_dump()
        # Without
        connector.object_check = False
        connector.restore_dump(dump)
        self.assertNotIn("--objcheck", mock_restore_cmd.call_args[0][0])
        # With
        connector.object_check = True
        connector.restore_dump(dump)
        self.assertIn(" --objcheck", mock_restore_cmd.call_args[0][0])

    @patch(
        "dbbackup.db.mongodb.MongoDumpConnector.run_command",
        return_value=(BytesIO(), BytesIO()),
    )
    def test_restore_dump_drop(self, mock_dump_cmd, mock_restore_cmd):
        connector = MongoDumpConnector()
        dump = connector.create_dump()
        # Without
        connector.drop = False
        connector.restore_dump(dump)
        self.assertNotIn("--drop", mock_restore_cmd.call_args[0][0])
        # With
        connector.drop = True
        connector.restore_dump(dump)
        self.assertIn(" --drop", mock_restore_cmd.call_args[0][0])
