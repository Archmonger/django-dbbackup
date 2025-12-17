import json
from unittest.mock import Mock, patch

import pytest
from django.conf import settings
from django.core.management.base import CommandError
from django.test import TestCase

from dbbackup.management.commands.dbrestore import Command as DbrestoreCommand


class DbrestoreMetadataTest(TestCase):
    def setUp(self):
        self.command = DbrestoreCommand()
        self.command.database_name = "default"
        self.command.logger = Mock()
        self.command.storage = Mock()
        self.command.path = None

    def test_metadata_match(self):
        # Setup metadata
        metadata = {"engine": settings.DATABASES["default"]["ENGINE"]}
        self.command.storage.read_file.return_value = Mock(read=lambda: json.dumps(metadata))

        # Should not raise
        self.command._check_metadata("backup.dump")

    def test_metadata_mismatch(self):
        # Setup metadata with different engine
        metadata = {"engine": "django.db.backends.postgresql"}
        self.command.storage.read_file.return_value = Mock(read=lambda: json.dumps(metadata))

        # Should raise
        with pytest.raises(CommandError) as cm:
            self.command._check_metadata("backup.dump")

        assert "Restoring to a different database engine is not supported" in str(cm.value)

    def test_no_metadata(self):
        # Setup storage to raise exception when reading metadata
        self.command.storage.read_file.side_effect = Exception("File not found")

        # Should not raise (backwards compatibility)
        self.command._check_metadata("backup.dump")

    def test_local_file_metadata_match(self):
        self.command.path = "local_backup.dump"
        metadata = {"engine": settings.DATABASES["default"]["ENGINE"]}

        with patch("os.path.exists", return_value=True), patch("builtins.open", new_callable=Mock) as mock_open:
            # Configure the mock to behave like a file object
            file_mock = Mock()
            file_mock.read.return_value = json.dumps(metadata)
            # Set up the context manager
            mock_open.return_value.__enter__ = Mock(return_value=file_mock)
            mock_open.return_value.__exit__ = Mock(return_value=None)

            self.command._check_metadata("local_backup.dump")

    def test_local_file_metadata_mismatch(self):
        self.command.path = "local_backup.dump"
        metadata = {"engine": "django.db.backends.postgresql"}

        with patch("os.path.exists", return_value=True), patch("builtins.open", new_callable=Mock) as mock_open:
            # Configure the mock to behave like a file object
            file_mock = Mock()
            file_mock.read.return_value = json.dumps(metadata)
            # Set up the context manager
            mock_open.return_value.__enter__ = Mock(return_value=file_mock)
            mock_open.return_value.__exit__ = Mock(return_value=None)

            with pytest.raises(CommandError):
                self.command._check_metadata("local_backup.dump")
