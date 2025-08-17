"""
Tests for dbrestore command.
"""

import shutil
from shutil import copyfileobj
from tempfile import mktemp
from unittest.mock import patch

from django.conf import settings
from django.core.files import File
from django.core.management.base import CommandError
from django.test import TestCase

from dbbackup import utils
from dbbackup.db.base import get_connector
from dbbackup.db.mongodb import MongoDumpConnector
from dbbackup.db.postgresql import PgDumpConnector
from dbbackup.management.commands.dbrestore import Command as DbrestoreCommand
from dbbackup.settings import HOSTNAME
from dbbackup.storage import get_storage
from tests.utils import (
    DEV_NULL,
    HANDLED_FILES,
    TARED_FILE,
    TEST_DATABASE,
    TEST_MONGODB,
    add_private_gpg,
    clean_gpg_keys,
    get_dump,
    get_dump_name,
)

GPG_AVAILABLE = shutil.which("gpg") is not None


@patch("dbbackup.management.commands._base.input", return_value="y")
class DbrestoreCommandRestoreBackupTest(TestCase):
    def setUp(self):
        self.command = DbrestoreCommand()
        self.command.stdout = DEV_NULL
        self.command.uncompress = False
        self.command.decrypt = False
        self.command.backup_extension = "bak"
        self.command.filename = "foofile"
        self.command.database = TEST_DATABASE
        self.command.passphrase = None
        self.command.interactive = True
        self.command.storage = get_storage()
        self.command.servername = HOSTNAME
        self.command.input_database_name = None
        self.command.database_name = "default"
        self.command.connector = get_connector("default")
        self.command.schemas = []
        HANDLED_FILES.clean()

    def tearDown(self):
        clean_gpg_keys()

    def test_no_filename(self, *args):
        # Prepare backup
        HANDLED_FILES["written_files"].append((utils.filename_generate("default"), File(get_dump())))
        # Check
        self.command.path = None
        self.command.filename = None
        self.command._restore_backup()

    def test_no_backup_found(self, *args):
        self.command.path = None
        self.command.filename = None
        with self.assertRaises(CommandError):
            self.command._restore_backup()

    def test_uncompress(self, *args):
        self.command.path = None
        compressed_file, self.command.filename = utils.compress_file(get_dump(), get_dump_name())
        HANDLED_FILES["written_files"].append((self.command.filename, File(compressed_file)))
        self.command.uncompress = True
        self.command._restore_backup()

    @patch("dbbackup.utils.getpass", return_value=None)
    def test_decrypt(self, *args):
        if not GPG_AVAILABLE:
            self.skipTest("gpg executable not available")
        add_private_gpg()
        self.command.path = None
        self.command.decrypt = True
        encrypted_file, self.command.filename = utils.encrypt_file(get_dump(), get_dump_name())
        HANDLED_FILES["written_files"].append((self.command.filename, File(encrypted_file)))
        self.command._restore_backup()

    def test_path(self, *args):
        temp_dump = get_dump()
        dump_path = mktemp()
        with open(dump_path, "wb") as dump:
            copyfileobj(temp_dump, dump)
        self.command.path = dump.name
        self.command._restore_backup()
        self.command.decrypt = False
        self.command.filepath = get_dump_name()
        HANDLED_FILES["written_files"].append((self.command.filepath, get_dump()))
        self.command._restore_backup()

    @patch("dbbackup.management.commands.dbrestore.get_connector")
    @patch("dbbackup.db.base.BaseDBConnector.restore_dump")
    def test_schema(self, mock_restore_dump, mock_get_connector, *args):
        """Schema is only used for postgresql."""
        mock_get_connector.return_value = PgDumpConnector()
        mock_restore_dump.return_value = True

        mock_file = File(get_dump())
        HANDLED_FILES["written_files"].append((self.command.filename, mock_file))

        with self.assertLogs("dbbackup.command", "INFO") as cm:
            # Without
            self.command.path = None
            self.command._restore_backup()
            self.assertEqual(self.command.connector.schemas, [])

            # With
            self.command.path = None
            self.command.schemas = ["public"]
            self.command._restore_backup()
            self.assertEqual(self.command.connector.schemas, ["public"])
            self.assertIn(
                "INFO:dbbackup.command:Restoring schemas: ['public']",
                cm.output,
            )

            # With multiple
            self.command.path = None
            self.command.schemas = ["public", "other"]
            self.command._restore_backup()
            self.assertEqual(self.command.connector.schemas, ["public", "other"])
            self.assertIn(
                "INFO:dbbackup.command:Restoring schemas: ['public', 'other']",
                cm.output,
            )

        mock_get_connector.assert_called_with("default")
        mock_restore_dump.assert_called_with(mock_file)


class DbrestoreCommandGetDatabaseTest(TestCase):
    def setUp(self):
        self.command = DbrestoreCommand()

    def test_give_db_name(self):
        name, db = self.command._get_database("default")
        self.assertEqual(name, "default")
        self.assertEqual(db, settings.DATABASES["default"])

    def test_no_given_db(self):
        name, db = self.command._get_database(None)
        self.assertEqual(name, "default")
        self.assertEqual(db, settings.DATABASES["default"])

    @patch("django.conf.settings.DATABASES", {"db1": {}, "db2": {}})
    def test_no_given_db_multidb(self):
        with self.assertRaises(CommandError):
            self.command._get_database({})


@patch("dbbackup.management.commands._base.input", return_value="y")
@patch(
    "dbbackup.management.commands.dbrestore.get_connector",
    return_value=MongoDumpConnector(),
)
@patch("dbbackup.db.mongodb.MongoDumpConnector.restore_dump")
class DbMongoRestoreCommandRestoreBackupTest(TestCase):
    def setUp(self):
        if not GPG_AVAILABLE:
            self.skipTest("gpg executable not available")
        self.command = DbrestoreCommand()
        self.command.stdout = DEV_NULL
        self.command.uncompress = False
        self.command.decrypt = False
        self.command.backup_extension = "bak"
        self.command.path = None
        self.command.filename = "foofile"
        self.command.database = TEST_MONGODB
        self.command.passphrase = None
        self.command.interactive = True
        self.command.storage = get_storage()
        self.command.connector = MongoDumpConnector()
        self.command.database_name = "mongo"
        self.command.input_database_name = None
        self.command.servername = HOSTNAME
        self.command.schemas = []
        HANDLED_FILES.clean()
        add_private_gpg()

    def test_mongo_settings_backup_command(self, mock_runcommands, *args):
        self.command.storage.file_read = TARED_FILE
        self.command.filename = TARED_FILE
        HANDLED_FILES["written_files"].append((TARED_FILE, open(TARED_FILE, "rb")))
        self.command._restore_backup()
        self.assertTrue(mock_runcommands.called)
