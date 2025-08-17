"""
Tests for dbbackup command.
"""

import os
import shutil
from unittest.mock import patch

GPG_AVAILABLE = shutil.which("gpg") is not None

from django.test import TestCase

from dbbackup.db.base import get_connector
from dbbackup.management.commands.dbbackup import Command as DbbackupCommand
from dbbackup.storage import get_storage
from tests.utils import DEV_NULL, TEST_DATABASE, add_public_gpg, clean_gpg_keys


@patch("dbbackup.settings.GPG_RECIPIENT", "test@test")
@patch("sys.stdout", DEV_NULL)
class DbbackupCommandSaveNewBackupTest(TestCase):
    def setUp(self):
        self.command = DbbackupCommand()
        self.command.servername = "foo-server"
        self.command.encrypt = False
        self.command.compress = False
        self.command.database = TEST_DATABASE["NAME"]
        self.command.storage = get_storage()
        self.command.connector = get_connector()
        self.command.stdout = DEV_NULL
        self.command.filename = None
        self.command.path = None
        self.command.schemas = []

    def tearDown(self):
        clean_gpg_keys()

    def test_func(self):
        self.command._save_new_backup(TEST_DATABASE)

    def test_compress(self):
        self.command.compress = True
        self.command._save_new_backup(TEST_DATABASE)

    def test_encrypt(self):
        if not GPG_AVAILABLE:
            self.skipTest("gpg executable not available")
        add_public_gpg()
        self.command.encrypt = True
        self.command._save_new_backup(TEST_DATABASE)

    def test_path(self):
        local_tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tmp")
        os.makedirs(local_tmp, exist_ok=True)
        self.command.path = os.path.join(local_tmp, "foo.bak")
        self.command._save_new_backup(TEST_DATABASE)
        self.assertTrue(os.path.exists(self.command.path))
        # tearDown
        os.remove(self.command.path)

    def test_schema(self):
        self.command.schemas = ["public"]
        result = self.command._save_new_backup(TEST_DATABASE)

        self.assertIsNone(result)

    @patch("dbbackup.settings.DATABASES", ["db-from-settings"])
    def test_get_database_keys(self):
        with self.subTest("use --database from CLI"):
            self.command.database = "db-from-cli"
            self.assertEqual(self.command._get_database_keys(), ["db-from-cli"])

        with self.subTest("fallback to DBBACKUP_DATABASES"):
            self.command.database = ""
            self.assertEqual(self.command._get_database_keys(), ["db-from-settings"])

        with self.subTest("multiple databases"):
            self.command.database = "db1,db2"
            self.assertEqual(self.command._get_database_keys(), ["db1", "db2"])

        with self.subTest("multiple databases with whitespace"):
            self.command.database = " db1 , db2 "
            self.assertEqual(self.command._get_database_keys(), ["db1", "db2"])

        with self.subTest("filter out empty strings to prevent get_connector('') bug"):
            self.command.database = "db1,,db2"
            self.assertEqual(self.command._get_database_keys(), ["db1", "db2"])

        with self.subTest("just comma returns empty list"):
            self.command.database = ","
            self.assertEqual(self.command._get_database_keys(), [])

        with self.subTest("just spaces returns empty list"):
            self.command.database = "  "
            self.assertEqual(self.command._get_database_keys(), [])


@patch("dbbackup.settings.GPG_RECIPIENT", "test@test")
@patch("sys.stdout", DEV_NULL)
@patch("dbbackup.db.sqlite.SqliteConnector.create_dump")
@patch("dbbackup.utils.handle_size", returned_value=4.2)
class DbbackupCommandSaveNewMongoBackupTest(TestCase):
    def setUp(self):
        self.command = DbbackupCommand()
        self.command.servername = "foo-server"
        self.command.encrypt = False
        self.command.compress = False
        self.command.storage = get_storage()
        self.command.stdout = DEV_NULL
        self.command.filename = None
        self.command.path = None
        self.command.connector = get_connector("default")
        self.command.schemas = []

    def tearDown(self):
        clean_gpg_keys()

    def test_func(self, mock_run_commands, mock_handle_size):
        self.command._save_new_backup(TEST_DATABASE)
        self.assertTrue(mock_run_commands.called)
