"""
Tests for Django native serializer connector.
"""

from tempfile import SpooledTemporaryFile
from unittest.mock import patch

from django.test import TestCase

from dbbackup.db.django import DjangoConnector


class DjangoConnectorTest(TestCase):
    """Tests for DjangoConnector."""

    def setUp(self):
        self.connector = DjangoConnector()

    def test_init(self):
        """Test connector initialization."""
        assert isinstance(self.connector, DjangoConnector)
        assert self.connector.extension == "json"

    @patch("dbbackup.db.django.call_command")
    def test_create_dump(self, mock_call_command):
        """Test dump creation using Django's dumpdata."""

        # Mock the dumpdata command to write JSON to stdout
        def mock_dumpdata(*args, **kwargs):
            if "stdout" in kwargs:
                kwargs["stdout"].write('[{"model": "auth.user", "pk": 1, "fields": {"username": "test"}}]')

        mock_call_command.side_effect = mock_dumpdata

        # Create the dump
        dump = self.connector.create_dump()

        # Verify call_command was called with correct parameters
        mock_call_command.assert_called_once()
        call_args = mock_call_command.call_args
        assert call_args[0] == ("dumpdata",)
        assert call_args[1]["format"] == "json"
        assert call_args[1]["verbosity"] == 0
        assert call_args[1]["use_natural_foreign_keys"]
        assert call_args[1]["use_natural_primary_keys"]

        # Verify dump content
        assert isinstance(dump, SpooledTemporaryFile)
        dump.seek(0)
        content = dump.read()  # Already a string in text mode
        assert '"model": "auth.user"' in content
        assert '"username": "test"' in content

    @patch("dbbackup.db.django.call_command")
    def test_create_dump_with_exclude_app_model_format(self, mock_call_command):
        """Test dump creation with exclude parameter in app.model format."""
        # Set exclude parameter with app.model format for available apps
        self.connector.exclude = ["testapp.CharModel"]

        # Mock the dumpdata command
        def mock_dumpdata(*args, **kwargs):
            if "stdout" in kwargs:
                kwargs["stdout"].write("[]")

        mock_call_command.side_effect = mock_dumpdata

        # Create the dump
        dump = self.connector.create_dump()

        # Verify call_command was called with correct exclude parameter
        mock_call_command.assert_called_once()
        call_args = mock_call_command.call_args
        # Should have exclude parameter since testapp.CharModel exists
        assert "exclude" in call_args[1]
        assert call_args[1]["exclude"] == ["testapp.CharModel"]
        assert isinstance(dump, SpooledTemporaryFile)

    @patch("dbbackup.db.django.call_command")
    def test_create_dump_with_exclude_table_names(self, mock_call_command):
        """Test dump creation with exclude parameter as table names."""
        # Set exclude parameter with table names that won't be converted
        # since auth app is not available in test environment
        self.connector.exclude = ["auth_user", "django_session"]

        # Mock the dumpdata command
        def mock_dumpdata(*args, **kwargs):
            if "stdout" in kwargs:
                kwargs["stdout"].write("[]")

        mock_call_command.side_effect = mock_dumpdata

        # Create the dump
        dump = self.connector.create_dump()

        # Verify call_command was called
        mock_call_command.assert_called_once()
        call_args = mock_call_command.call_args
        # Should NOT have exclude parameter since auth/sessions apps don't exist
        # and table names can't be converted
        assert "exclude" not in call_args[1]
        assert isinstance(dump, SpooledTemporaryFile)

    @patch("dbbackup.db.django.call_command")
    def test_create_dump_with_exclude_mixed_format(self, mock_call_command):
        """Test dump creation with exclude parameter in mixed formats."""
        # Set exclude parameter with mixed formats - valid and invalid
        self.connector.exclude = ["testapp.TextModel", "auth_user", "unknown_table"]

        # Mock the dumpdata command
        def mock_dumpdata(*args, **kwargs):
            if "stdout" in kwargs:
                kwargs["stdout"].write("[]")

        mock_call_command.side_effect = mock_dumpdata

        # Create the dump
        dump = self.connector.create_dump()

        # Verify call_command was called with properly handled exclude parameter
        mock_call_command.assert_called_once()
        call_args = mock_call_command.call_args
        # Should have exclude parameter with only the valid testapp.TextModel
        assert "exclude" in call_args[1]
        assert call_args[1]["exclude"] == ["testapp.TextModel"]
        assert isinstance(dump, SpooledTemporaryFile)

    @patch("dbbackup.db.django.call_command")
    def test_create_dump_with_exclude_invalid_only(self, mock_call_command):
        """Test dump creation with exclude parameter containing only invalid entries."""
        # Set exclude parameter with only invalid entries
        self.connector.exclude = ["nonexistent.Model", "auth_user", "unknown_table"]

        # Mock the dumpdata command
        def mock_dumpdata(*args, **kwargs):
            if "stdout" in kwargs:
                kwargs["stdout"].write("[]")

        mock_call_command.side_effect = mock_dumpdata

        # Create the dump
        dump = self.connector.create_dump()

        # Verify call_command was called without exclude parameter
        mock_call_command.assert_called_once()
        call_args = mock_call_command.call_args
        # Should NOT have exclude parameter since all entries are invalid
        assert "exclude" not in call_args[1]
        assert isinstance(dump, SpooledTemporaryFile)

    @patch("dbbackup.db.django.call_command")
    @patch("dbbackup.db.django.os.unlink")
    def test_restore_dump(self, mock_unlink, mock_call_command):
        """Test dump restoration using Django's loaddata."""
        # Create a mock dump file in text mode (consistent with new create_dump behavior)
        dump_content = '[{"model": "auth.user", "pk": 1, "fields": {"username": "test"}}]'
        dump = SpooledTemporaryFile(mode="w+t", encoding="utf-8")
        dump.write(dump_content)
        dump.seek(0)

        # Restore the dump
        self.connector.restore_dump(dump)

        # Verify call_command was called with loaddata
        mock_call_command.assert_called_once()
        call_args = mock_call_command.call_args
        assert call_args[0][0] == "loaddata"
        assert call_args[1]["verbosity"] == 0

        # Verify temporary file was cleaned up
        mock_unlink.assert_called_once()

    @patch("dbbackup.db.django.call_command")
    @patch("dbbackup.db.django.os.unlink")
    def test_restore_dump_with_django_file(self, mock_unlink, mock_call_command):
        """Test dump restoration with Django File object."""
        from django.core.files.base import ContentFile

        # Create a mock Django File
        dump_content = '[{"model": "auth.user", "pk": 1, "fields": {"username": "test"}}]'
        dump = ContentFile(dump_content.encode("utf-8"))

        # Restore the dump
        self.connector.restore_dump(dump)

        # Verify call_command was called with loaddata
        mock_call_command.assert_called_once()
        call_args = mock_call_command.call_args
        assert call_args[0][0] == "loaddata"
        assert call_args[1]["verbosity"] == 0

        # Verify temporary file was cleaned up
        mock_unlink.assert_called_once()

    @patch("dbbackup.db.django.call_command")
    @patch("dbbackup.db.django.os.unlink")
    def test_restore_dump_cleanup_failure(self, mock_unlink, mock_call_command):
        """Test that cleanup failure doesn't raise an exception."""
        # Make unlink raise an exception
        mock_unlink.side_effect = OSError("File not found")

        # Create a mock dump file in text mode (consistent with new create_dump behavior)
        dump_content = "[]"
        dump = SpooledTemporaryFile(mode="w+t", encoding="utf-8")
        dump.write(dump_content)
        dump.seek(0)

        # This should not raise an exception despite unlink failure
        self.connector.restore_dump(dump)

        # Verify call_command was still called
        mock_call_command.assert_called_once()

    def test_generate_filename(self):
        """Test filename generation."""
        filename = self.connector.generate_filename()
        assert filename.endswith(".json")

    @patch("dbbackup.db.django.call_command")
    def test_integration_create_and_restore(self, mock_call_command):
        """Test integration between create_dump and restore_dump."""
        # Mock dumpdata to return some JSON
        dump_content = '[{"model": "auth.user", "pk": 1, "fields": {"username": "testuser"}}]'

        def mock_dumpdata(*args, **kwargs):
            if "stdout" in kwargs:
                kwargs["stdout"].write(dump_content)

        mock_call_command.side_effect = mock_dumpdata

        # Create dump
        dump = self.connector.create_dump()

        # Verify dumpdata was called
        assert mock_call_command.call_count == 1

        # Reset mock for restore
        mock_call_command.reset_mock()
        mock_call_command.side_effect = None

        # Restore dump
        with patch("dbbackup.db.django.os.unlink"):
            self.connector.restore_dump(dump)

        # Verify loaddata was called
        assert mock_call_command.call_count == 1
