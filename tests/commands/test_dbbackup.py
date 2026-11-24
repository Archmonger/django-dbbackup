"""
Tests for dbbackup command.
"""

import os
import shutil
from unittest.mock import patch

GPG_AVAILABLE = shutil.which("gpg") is not None

import pytest
from django.test import TestCase

from dbbackup.db.base import get_connector
from dbbackup.management.commands.dbbackup import Command as DbbackupCommand
from dbbackup.storage import get_storage
from tests.utils import (
    DEV_NULL,
    HANDLED_FILES,
    TEST_DATABASE,
    add_public_gpg,
    clean_gpg_keys,
)


@patch("dbbackup.settings.GPG_RECIPIENT", "test@test")
@patch("sys.stdout", DEV_NULL)
class DbbackupCommandSaveNewBackupTest(TestCase):
    def setUp(self):
        HANDLED_FILES.clean()
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
        assert len(HANDLED_FILES["written_files"]) == 2
        assert HANDLED_FILES["written_files"][0][0].endswith(".gz")
        assert HANDLED_FILES["written_files"][1][0].endswith(".gz.metadata")

    def test_encrypt(self):
        if not GPG_AVAILABLE:
            self.skipTest("gpg executable not available")
        add_public_gpg()
        self.command.encrypt = True
        self.command._save_new_backup(TEST_DATABASE)
        assert len(HANDLED_FILES["written_files"]) == 2
        assert HANDLED_FILES["written_files"][0][0].endswith(".gpg")
        assert HANDLED_FILES["written_files"][1][0].endswith(".gpg.metadata")

    def test_path(self):
        local_tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tmp")
        os.makedirs(local_tmp, exist_ok=True)
        self.command.path = os.path.join(local_tmp, "foo.bak")
        self.command._save_new_backup(TEST_DATABASE)
        assert os.path.exists(self.command.path)
        assert os.path.exists(f"{self.command.path}.metadata")
        # tearDown
        os.remove(self.command.path)
        os.remove(f"{self.command.path}.metadata")

    def test_schema(self):
        self.command.schemas = ["public"]
        result = self.command._save_new_backup(TEST_DATABASE)

        assert result is None

    def test_metadata_is_bytes(self):
        """Test that metadata content is passed as bytes to storage."""
        self.command._save_new_backup(TEST_DATABASE)

        # Find the metadata file in HANDLED_FILES
        # HANDLED_FILES["written_files"] contains tuples (name, file_object)
        metadata_file_entry = next((f for f in HANDLED_FILES["written_files"] if f[0].endswith(".metadata")), None)
        assert metadata_file_entry is not None

        metadata_file = metadata_file_entry[1]
        metadata_file.open()
        content = metadata_file.read()

        # Check if content is bytes
        assert isinstance(content, bytes), f"Metadata content should be bytes, but got {type(content)}"

    @patch("dbbackup.management.commands._base.BaseDbBackupCommand.write_to_storage")
    def test_path_s3_uri(self, mock_write_to_storage):
        """Test that S3 URIs in output path are handled by write_to_storage instead of write_local_file."""
        self.command.path = "s3://mybucket/backups/db.bak"
        self.command._save_new_backup(TEST_DATABASE)
        assert mock_write_to_storage.called
        # Verify the S3 path was passed correctly to write_to_storage
        # The first call should be the backup file
        args, _kwargs = mock_write_to_storage.call_args_list[0]
        assert args[1] == "s3://mybucket/backups/db.bak"

    @patch("dbbackup.management.commands._base.BaseDbBackupCommand.write_to_storage")
    def test_path_s3_uri_variants(self, mock_write_to_storage):
        """Test various S3 URI formats."""
        test_cases = [
            "s3://bucket/file.bak",
            "s3://bucket/folder/file.bak",
            "s3://bucket-with-dashes/nested/folders/file.bak",
            "s3://bucket/path/without/trailing/slash",
        ]

        for s3_uri in test_cases:
            with self.subTest(s3_uri=s3_uri):
                mock_write_to_storage.reset_mock()
                self.command.path = s3_uri
                self.command._save_new_backup(TEST_DATABASE)
                assert mock_write_to_storage.called
                # The first call should be the backup file
                args, _kwargs = mock_write_to_storage.call_args_list[0]
                assert args[1] == s3_uri

    def test_path_local_file_still_works(self):
        """Test that regular local file paths still use write_local_file."""
        local_tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tmp")
        os.makedirs(local_tmp, exist_ok=True)

        # Test with a real local path that should work
        local_path = os.path.join(local_tmp, "test_local.bak")
        self.command.path = local_path
        self.command._save_new_backup(TEST_DATABASE)

        # Verify the file was created (meaning write_local_file was used)
        assert os.path.exists(local_path)
        assert os.path.exists(f"{local_path}.metadata")

        # Cleanup
        os.remove(local_path)
        os.remove(f"{local_path}.metadata")

        # Test that paths containing 's3' but not starting with 's3://' are treated as local
        with patch("dbbackup.management.commands._base.BaseDbBackupCommand.write_local_file") as mock_write_local_file:
            mock_write_local_file.side_effect = FileNotFoundError("Mocked error")

            test_cases = [
                "/path/with/s3/in/name/backup.bak",
                "s3_backup.bak",  # starts with s3 but not s3://
                "bucket-s3-backup.bak",
            ]

            for local_path in test_cases:
                with self.subTest(local_path=local_path):
                    mock_write_local_file.reset_mock()
                    self.command.path = local_path
                    # This should call write_local_file (and raise our mocked error)
                    with pytest.raises(FileNotFoundError):
                        self.command._save_new_backup(TEST_DATABASE)
                    # Verify write_local_file was called
                    assert mock_write_local_file.called
                    args, _kwargs = mock_write_local_file.call_args
                    assert args[1] == local_path

    @patch("dbbackup.settings.DATABASES", ["db-from-settings"])
    def test_get_database_keys(self):
        with self.subTest("use --database from CLI"):
            self.command.database = "db-from-cli"
            assert self.command._get_database_keys() == ["db-from-cli"]

        with self.subTest("fallback to DBBACKUP_DATABASES"):
            self.command.database = ""
            assert self.command._get_database_keys() == ["db-from-settings"]

        with self.subTest("multiple databases"):
            self.command.database = "db1,db2"
            assert self.command._get_database_keys() == ["db1", "db2"]

        with self.subTest("multiple databases with whitespace"):
            self.command.database = " db1 , db2 "
            assert self.command._get_database_keys() == ["db1", "db2"]

        with self.subTest("filter out empty strings to prevent get_connector('') bug"):
            self.command.database = "db1,,db2"
            assert self.command._get_database_keys() == ["db1", "db2"]

        with self.subTest("just comma returns empty list"):
            self.command.database = ","
            assert self.command._get_database_keys() == []

        with self.subTest("just spaces returns empty list"):
            self.command.database = "  "
            assert self.command._get_database_keys() == []


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
        assert mock_run_commands.called
