"""
Tests for dbrestore command.
"""

import io
import shutil
from io import BytesIO
from shutil import copyfileobj
from tempfile import mktemp
from unittest.mock import Mock, patch

import pytest
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
        with pytest.raises(CommandError):
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
            assert self.command.connector.schemas == []

            # With
            self.command.path = None
            self.command.schemas = ["public"]
            self.command._restore_backup()
            assert self.command.connector.schemas == ["public"]
            assert "INFO:dbbackup.command:Restoring schemas: ['public']" in cm.output

            # With multiple
            self.command.path = None
            self.command.schemas = ["public", "other"]
            self.command._restore_backup()
            assert self.command.connector.schemas == ["public", "other"]
            assert "INFO:dbbackup.command:Restoring schemas: ['public', 'other']" in cm.output

        mock_get_connector.assert_called_with("default")
        mock_restore_dump.assert_called_with(mock_file)


class MockFTPFile(BytesIO):
    """Mock file object similar to what FTP storage returns without fileno() support."""

    def __init__(self, content: bytes):
        super().__init__(content)
        self.name = "test-backup.psql.bin"
        # Keep original payload so repeated open() calls return a fresh BytesIO
        # instance (mimics Django Storage behavior) and avoid dead-code warning.
        self._file_content = content

    def fileno(self):
        """Simulate FTP file object that doesn't support fileno()."""
        msg = "fileno"
        raise io.UnsupportedOperation(msg)

    def open(self, mode: str = "rb"):
        """Return a new readable stream each time open() is called."""
        return BytesIO(self._file_content)


@patch("dbbackup.management.commands._base.input", return_value="y")
class DbrestoreCommandFTPFileTest(TestCase):
    """Test restore functionality with FTP-like file objects that don't support fileno()."""

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
        self.command.schemas = []
        HANDLED_FILES.clean()

    @patch("dbbackup.management.commands.dbrestore.get_connector")
    def test_ftp_file_restore_with_postgresql(self, mock_get_connector, *args):
        """Test that restore works with FTP-like files that don't support fileno() using PostgreSQL."""
        # Create mock PgDumpBinaryConnector that would trigger the fileno() issue
        mock_connector = Mock(spec=PgDumpConnector)
        mock_connector.schemas = []
        mock_get_connector.return_value = mock_connector

        # Create mock FTP file with dump content
        dump_content = get_dump().read()
        ftp_file = MockFTPFile(dump_content)

        # Mock the storage to return our FTP-like file
        with patch.object(self.command.storage, "read_file", return_value=ftp_file):
            # Ensure the backup filename exists in storage
            HANDLED_FILES["written_files"].append((self.command.filename, File(BytesIO(dump_content))))

            # Set up command with PostgreSQL connector
            self.command.connector = mock_connector

            # This should not raise io.UnsupportedOperation: fileno when using external tools
            self.command.path = None
            self.command._restore_backup()

            # Verify the restore_dump was called with a file object
            mock_connector.restore_dump.assert_called_once()

            # Get the file object that was passed to restore_dump
            called_file = mock_connector.restore_dump.call_args[0][0]

            # The file should be converted to a SpooledTemporaryFile with content
            assert called_file is not None
            # Verify content is preserved
            called_file.seek(0)
            assert called_file.read() == dump_content


class DbrestoreCommandGetDatabaseTest(TestCase):
    def setUp(self):
        self.command = DbrestoreCommand()

    def test_give_db_name(self):
        name, db = self.command._get_database("default")
        assert name == "default"
        assert db == settings.DATABASES["default"]

    def test_no_given_db(self):
        name, db = self.command._get_database(None)
        assert name == "default"
        assert db == settings.DATABASES["default"]

    @patch("django.conf.settings.DATABASES", {"db1": {}, "db2": {}})
    def test_no_given_db_multidb(self):
        with pytest.raises(CommandError):
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
        with open(TARED_FILE, "rb") as f:
            HANDLED_FILES["written_files"].append((TARED_FILE, f))
            self.command._restore_backup()
            assert mock_runcommands.called
