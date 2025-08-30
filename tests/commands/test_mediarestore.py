"""
Tests for mediarestore command.
"""

from io import BytesIO
from unittest.mock import patch

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
        from unittest.mock import Mock

        self.command.logger = Mock()

        # Create a mock file
        mock_file = BytesIO(b"test content")

        # Call _upload_file - should delete existing file then save
        self.command._upload_file("test.txt", mock_file)

        # Should call delete then save
        mock_storage.delete.assert_called_once_with("test.txt")
        mock_storage.save.assert_called_once_with("test.txt", mock_file)
