"""
Tests for mediarestore command.
"""

import gzip
import tarfile
from io import BytesIO
from unittest.mock import Mock, patch

from django.test import TestCase

from dbbackup.management.commands.mediarestore import Command


class MediarestoreCommandTest(TestCase):
    def setUp(self):
        self.command = Command()
        # Initialize required attributes
        self.command.servername = None
        self.command.replace = False
        self.command.media_storage = None
        self.command.logger = None

    @patch("dbbackup.management.commands.mediarestore.get_storage_class")
    def test_restore_backup_with_existing_file_no_replace(self, mock_get_storage_class):
        """Test restore when file exists and replace=False"""
        # Create a mock storage that indicates file exists
        mock_storage = mock_get_storage_class.return_value.return_value
        mock_storage.exists.return_value = True
        self.command.media_storage = mock_storage

        # Set replace to False
        self.command.replace = False

        # Create a mock file
        mock_file = BytesIO(b"test content")

        # Call _upload_file - should return early due to exists() and not replace
        result = self.command._upload_file("test.txt", mock_file)

        # Should not call save since file exists and replace=False
        assert result is None
        mock_storage.save.assert_not_called()

    @patch("dbbackup.management.commands.mediarestore.get_storage_class")
    def test_restore_backup_with_existing_file_with_replace(self, mock_get_storage_class):
        """Test restore when file exists and replace=True"""
        # Create a mock storage that indicates file exists
        mock_storage = mock_get_storage_class.return_value.return_value
        mock_storage.exists.return_value = True
        self.command.media_storage = mock_storage

        # Set replace to True
        self.command.replace = True

        # Create a mock logger
        self.command.logger = Mock()

        # Create a mock file
        mock_file = BytesIO(b"test content")

        # Call _upload_file - should delete existing file then save
        self.command._upload_file("test.txt", mock_file)

        # Should call delete then save
        mock_storage.delete.assert_called_once_with("test.txt")
        mock_storage.save.assert_called_once_with("test.txt", mock_file)

    def _create_tar_with_test_file(self):
        """Helper method to create a tar file with test content"""
        tar_buffer = BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            # Add a test file to the tar
            test_content = b"test file content"
            test_file_info = tarfile.TarInfo(name="test.txt")
            test_file_info.size = len(test_content)
            tar.addfile(test_file_info, BytesIO(test_content))
        return tar_buffer

    def _setup_mocks_for_restore(self):
        """Helper method to set up common mocks for restore tests"""
        mock_storage = Mock()
        mock_media_storage = Mock()
        mock_media_storage.exists.return_value = False

        self.command.storage = mock_storage
        self.command.media_storage = mock_media_storage
        self.command.servername = "test-server"
        self.command.passphrase = None
        self.command.logger = Mock()

        return mock_media_storage

    def test_restore_compressed_backup(self):
        """Test restore of a compressed (gzipped) tar backup"""
        self.command.uncompress = True
        self.command.decrypt = False
        self.command.interactive = False
        self.command.replace = False

        # Create a compressed tar file with test content
        tar_buffer = self._create_tar_with_test_file()

        # Compress the tar file
        tar_buffer.seek(0)
        compressed_buffer = BytesIO()
        with gzip.GzipFile(fileobj=compressed_buffer, mode="wb") as gz:
            gz.write(tar_buffer.read())

        compressed_buffer.seek(0)

        # Set up mocks
        mock_media_storage = self._setup_mocks_for_restore()

        # Mock _get_backup_file to return our compressed file
        with patch.object(self.command, "_get_backup_file") as mock_get_backup:
            mock_get_backup.return_value = ("test-backup.tar.gz", compressed_buffer)

            # This should not raise an exception
            self.command._restore_backup()

            # Verify that the file was uploaded
            mock_media_storage.save.assert_called_once()

    def test_restore_uncompressed_backup(self):
        """Test restore of an uncompressed tar backup"""
        self.command.uncompress = False
        self.command.decrypt = False
        self.command.interactive = False
        self.command.replace = False

        # Create an uncompressed tar file with test content
        tar_buffer = self._create_tar_with_test_file()
        tar_buffer.seek(0)

        # Set up mocks
        mock_media_storage = self._setup_mocks_for_restore()

        # Mock _get_backup_file to return our uncompressed file
        with patch.object(self.command, "_get_backup_file") as mock_get_backup:
            mock_get_backup.return_value = ("test-backup.tar", tar_buffer)

            # This should not raise an exception
            self.command._restore_backup()

            # Verify that the file was uploaded
            mock_media_storage.save.assert_called_once()
