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

    def test_django_connector_mismatch_allowed(self):
        # Setup metadata with different engine but DjangoConnector
        metadata = {
            "engine": "django.db.backends.postgresql",
            "connector": "dbbackup.db.django.DjangoConnector",
        }
        self.command.storage.read_file.return_value = Mock(read=lambda: json.dumps(metadata))

        # Should not raise
        self.command._check_metadata("backup.dump")


class DbrestoreConnectorOverrideTest(TestCase):
    def setUp(self):
        self.command = DbrestoreCommand()
        self.command.database_name = "default"
        self.command.logger = Mock()
        self.command.storage = Mock()
        self.command.path = None
        self.command.interactive = False
        self.command.decrypt = False
        self.command.uncompress = False
        self.command.schemas = []
        self.command.no_drop = False
        self.command.pg_options = ""
        self.command.servername = "testserver"
        self.command.input_database_name = "default"
        self.command.database = settings.DATABASES["default"]

        # Mock _get_backup_file
        mock_file = Mock()
        mock_file.fileno.return_value = 1
        mock_file.size = 1024
        self.command._get_backup_file = Mock(return_value=("backup.dump", mock_file))

        # Mock _ask_confirmation
        self.command._ask_confirmation = Mock()

    @patch("dbbackup.management.commands.dbrestore.get_connector")
    @patch("dbbackup.management.commands.dbrestore.import_module")
    def test_connector_override(self, mock_import_module, mock_get_connector):
        # Setup metadata with a specific connector
        metadata = {"engine": settings.DATABASES["default"]["ENGINE"], "connector": "my.custom.Connector"}
        self.command.storage.read_file.return_value = Mock(read=lambda: json.dumps(metadata))

        # Mock the custom connector class
        mock_module = Mock()
        mock_connector_class = Mock()
        mock_connector_instance = Mock()
        mock_connector_class.return_value = mock_connector_instance

        mock_import_module.return_value = mock_module
        mock_module.Connector = mock_connector_class

        # Run restore
        self.command._restore_backup()

        # Verify import_module was called with "my.custom"
        mock_import_module.assert_called_with("my.custom")

        # Verify connector was instantiated
        mock_connector_class.assert_called_with("default")

        # Verify self.command.connector is the custom one
        assert self.command.connector == mock_connector_instance

        # Verify get_connector was NOT called
        mock_get_connector.assert_not_called()

    @patch("dbbackup.management.commands.dbrestore.get_connector")
    def test_connector_fallback_on_import_error(self, mock_get_connector):
        # Setup metadata with a specific connector that fails to import
        metadata = {"engine": settings.DATABASES["default"]["ENGINE"], "connector": "my.broken.Connector"}
        self.command.storage.read_file.return_value = Mock(read=lambda: json.dumps(metadata))

        # Mock default connector
        mock_default_connector = Mock()
        mock_get_connector.return_value = mock_default_connector

        # We don't mock import_module, so it will raise ImportError (or we can mock it to raise)
        with patch("dbbackup.management.commands.dbrestore.import_module", side_effect=ImportError):
            self.command._restore_backup()

        # Verify get_connector WAS called
        mock_get_connector.assert_called_with("default")

        # Verify self.command.connector is the default one
        assert self.command.connector == mock_default_connector

    @patch("dbbackup.management.commands.dbrestore.get_connector")
    @patch("builtins.input", return_value="y")
    def test_connector_fallback_interactive_yes(self, mock_input, mock_get_connector):
        self.command.interactive = True
        # Setup metadata with a specific connector that fails to import
        metadata = {"engine": settings.DATABASES["default"]["ENGINE"], "connector": "my.broken.Connector"}
        self.command.storage.read_file.return_value = Mock(read=lambda: json.dumps(metadata))

        # Mock default connector
        mock_default_connector = Mock()
        mock_get_connector.return_value = mock_default_connector

        with patch("dbbackup.management.commands.dbrestore.import_module", side_effect=ImportError):
            self.command._restore_backup()

        # Verify input was called
        mock_input.assert_called()
        # Verify get_connector WAS called
        mock_get_connector.assert_called_with("default")

    @patch("dbbackup.management.commands.dbrestore.get_connector")
    @patch("builtins.input", return_value="n")
    def test_connector_fallback_interactive_no(self, mock_input, mock_get_connector):
        self.command.interactive = True
        # Setup metadata with a specific connector that fails to import
        metadata = {"engine": settings.DATABASES["default"]["ENGINE"], "connector": "my.broken.Connector"}
        self.command.storage.read_file.return_value = Mock(read=lambda: json.dumps(metadata))

        with patch("dbbackup.management.commands.dbrestore.import_module", side_effect=ImportError):
            with pytest.raises(SystemExit):
                self.command._restore_backup()

        # Verify input was called
        mock_input.assert_called()
        # Verify get_connector was NOT called
        mock_get_connector.assert_not_called()
