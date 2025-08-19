"""
Tests for Django native serializer connector.
"""

from io import StringIO
from unittest.mock import patch, MagicMock
from tempfile import SpooledTemporaryFile

from django.test import TestCase
from django.core.management import call_command

from dbbackup.db.django import DjangoConnector


class DjangoConnectorTest(TestCase):
    """Tests for DjangoConnector."""

    def setUp(self):
        self.connector = DjangoConnector()

    def test_init(self):
        """Test connector initialization."""
        self.assertIsInstance(self.connector, DjangoConnector)
        self.assertEqual(self.connector.extension, "json")

    @patch('dbbackup.db.django.call_command')
    def test_create_dump(self, mock_call_command):
        """Test dump creation using Django's dumpdata."""
        # Mock the dumpdata command to write JSON to stdout
        def mock_dumpdata(*args, **kwargs):
            if 'stdout' in kwargs:
                kwargs['stdout'].write('[{"model": "auth.user", "pk": 1, "fields": {"username": "test"}}]')
        
        mock_call_command.side_effect = mock_dumpdata
        
        # Create the dump
        dump = self.connector.create_dump()
        
        # Verify call_command was called with correct parameters
        mock_call_command.assert_called_once()
        call_args = mock_call_command.call_args
        self.assertEqual(call_args[0], ('dumpdata',))
        self.assertEqual(call_args[1]['format'], 'json')
        self.assertEqual(call_args[1]['verbosity'], 0)
        self.assertTrue(call_args[1]['use_natural_foreign_keys'])
        self.assertTrue(call_args[1]['use_natural_primary_keys'])
        
        # Verify dump content
        self.assertIsInstance(dump, SpooledTemporaryFile)
        dump.seek(0)
        content = dump.read().decode('utf-8')
        self.assertIn('"model": "auth.user"', content)
        self.assertIn('"username": "test"', content)

    @patch('dbbackup.db.django.call_command')
    def test_create_dump_with_exclude(self, mock_call_command):
        """Test dump creation with exclude parameter."""
        # Set exclude parameter
        self.connector.exclude = ['auth.user', 'sessions.session']
        
        # Mock the dumpdata command
        def mock_dumpdata(*args, **kwargs):
            if 'stdout' in kwargs:
                kwargs['stdout'].write('[]')
        
        mock_call_command.side_effect = mock_dumpdata
        
        # Create the dump
        dump = self.connector.create_dump()
        
        # Verify call_command was called
        mock_call_command.assert_called_once()
        self.assertIsInstance(dump, SpooledTemporaryFile)

    @patch('dbbackup.db.django.call_command')
    @patch('dbbackup.db.django.os.unlink')
    def test_restore_dump(self, mock_unlink, mock_call_command):
        """Test dump restoration using Django's loaddata."""
        # Create a mock dump file
        dump_content = '[{"model": "auth.user", "pk": 1, "fields": {"username": "test"}}]'
        dump = SpooledTemporaryFile(mode='w+b')
        dump.write(dump_content.encode('utf-8'))
        dump.seek(0)
        
        # Restore the dump
        self.connector.restore_dump(dump)
        
        # Verify call_command was called with loaddata
        mock_call_command.assert_called_once()
        call_args = mock_call_command.call_args
        self.assertEqual(call_args[0][0], 'loaddata')
        self.assertEqual(call_args[1]['verbosity'], 0)
        
        # Verify temporary file was cleaned up
        mock_unlink.assert_called_once()

    @patch('dbbackup.db.django.call_command')
    @patch('dbbackup.db.django.os.unlink')
    def test_restore_dump_with_django_file(self, mock_unlink, mock_call_command):
        """Test dump restoration with Django File object."""
        from django.core.files.base import ContentFile
        
        # Create a mock Django File
        dump_content = '[{"model": "auth.user", "pk": 1, "fields": {"username": "test"}}]'
        dump = ContentFile(dump_content.encode('utf-8'))
        
        # Restore the dump
        self.connector.restore_dump(dump)
        
        # Verify call_command was called with loaddata
        mock_call_command.assert_called_once()
        call_args = mock_call_command.call_args
        self.assertEqual(call_args[0][0], 'loaddata')
        self.assertEqual(call_args[1]['verbosity'], 0)
        
        # Verify temporary file was cleaned up
        mock_unlink.assert_called_once()

    @patch('dbbackup.db.django.call_command')
    @patch('dbbackup.db.django.os.unlink')
    def test_restore_dump_cleanup_failure(self, mock_unlink, mock_call_command):
        """Test that cleanup failure doesn't raise an exception."""
        # Make unlink raise an exception
        mock_unlink.side_effect = OSError("File not found")
        
        # Create a mock dump file
        dump_content = '[]'
        dump = SpooledTemporaryFile(mode='w+b')
        dump.write(dump_content.encode('utf-8'))
        dump.seek(0)
        
        # This should not raise an exception despite unlink failure
        self.connector.restore_dump(dump)
        
        # Verify call_command was still called
        mock_call_command.assert_called_once()

    def test_generate_filename(self):
        """Test filename generation."""
        filename = self.connector.generate_filename()
        self.assertTrue(filename.endswith('.json'))

    @patch('dbbackup.db.django.call_command')
    def test_integration_create_and_restore(self, mock_call_command):
        """Test integration between create_dump and restore_dump."""
        # Mock dumpdata to return some JSON
        dump_content = '[{"model": "auth.user", "pk": 1, "fields": {"username": "testuser"}}]'
        
        def mock_dumpdata(*args, **kwargs):
            if 'stdout' in kwargs:
                kwargs['stdout'].write(dump_content)
        
        mock_call_command.side_effect = mock_dumpdata
        
        # Create dump
        dump = self.connector.create_dump()
        
        # Verify dumpdata was called
        self.assertEqual(mock_call_command.call_count, 1)
        
        # Reset mock for restore
        mock_call_command.reset_mock()
        mock_call_command.side_effect = None
        
        # Restore dump
        with patch('dbbackup.db.django.os.unlink'):
            self.connector.restore_dump(dump)
        
        # Verify loaddata was called
        self.assertEqual(mock_call_command.call_count, 1)