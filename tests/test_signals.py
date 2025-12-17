"""Test Django signals functionality."""

from unittest.mock import Mock, patch

from django.test import TestCase

from dbbackup import signals
from dbbackup.management.commands.dbbackup import Command as DbBackupCommand
from dbbackup.management.commands.dbrestore import Command as DbRestoreCommand
from dbbackup.management.commands.mediabackup import Command as MediaBackupCommand
from dbbackup.management.commands.mediarestore import Command as MediaRestoreCommand
from dbbackup.storage import get_storage


class SignalsTestCase(TestCase):
    """Test that signals are properly sent during backup and restore operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.received_signals = []

    def signal_receiver(self, sender, **kwargs):
        """Generic signal receiver that records signal data."""
        self.received_signals.append({"sender": sender, "kwargs": kwargs})

    def test_pre_backup_signal_sent(self):
        """Test that pre_backup signal is sent before database backup."""
        signals.pre_backup.connect(self.signal_receiver)

        command = DbBackupCommand()
        command.storage = get_storage()
        command.servername = "test-server"
        command.schemas = []
        command.filename = None
        command.path = None
        command.compress = False
        command.encrypt = False
        command.logger = Mock()

        # Mock the connector and its methods
        mock_connector = Mock()
        mock_connector.generate_filename.return_value = "test_backup.sql"
        mock_connector.connection.settings_dict = {"ENGINE": "django.db.backends.sqlite3"}

        # Create a proper mock for the file object
        mock_file = Mock()
        mock_file.size = 1024  # Mock size as integer
        mock_file.seek = Mock()
        mock_file.tell = Mock(return_value=1024)
        mock_connector.create_dump.return_value = mock_file
        command.connector = mock_connector

        # Mock the write methods to avoid actual storage operations
        command.write_to_storage = Mock()
        command.write_local_file = Mock()

        database = {"NAME": "test_db"}

        command._save_new_backup(database)

        # Verify pre_backup signal was sent
        assert len(self.received_signals) == 1
        pre_signal = self.received_signals[0]
        assert pre_signal["sender"] == DbBackupCommand
        assert pre_signal["kwargs"]["database"] == database
        assert pre_signal["kwargs"]["connector"] == mock_connector
        assert pre_signal["kwargs"]["servername"] == "test-server"

        signals.pre_backup.disconnect(self.signal_receiver)

    def test_post_backup_signal_sent(self):
        """Test that post_backup signal is sent after database backup."""
        signals.post_backup.connect(self.signal_receiver)

        command = DbBackupCommand()
        command.storage = get_storage()
        command.servername = "test-server"
        command.schemas = []
        command.filename = None
        command.path = None
        command.compress = False
        command.encrypt = False
        command.logger = Mock()

        # Mock the connector and its methods
        mock_connector = Mock()
        mock_connector.generate_filename.return_value = "test_backup.sql"
        mock_connector.connection.settings_dict = {"ENGINE": "django.db.backends.sqlite3"}

        # Create a proper mock for the file object
        mock_file = Mock()
        mock_file.size = 1024  # Mock size as integer
        mock_file.seek = Mock()
        mock_file.tell = Mock(return_value=1024)
        mock_connector.create_dump.return_value = mock_file
        command.connector = mock_connector

        # Mock the write methods to avoid actual storage operations
        command.write_to_storage = Mock()
        command.write_local_file = Mock()

        database = {"NAME": "test_db"}

        command._save_new_backup(database)

        # Verify post_backup signal was sent - it should be the last signal
        assert len(self.received_signals) >= 1
        post_signal = self.received_signals[-1]  # Get the last signal
        assert post_signal["sender"] == DbBackupCommand
        assert post_signal["kwargs"]["database"] == database
        assert post_signal["kwargs"]["connector"] == mock_connector
        assert post_signal["kwargs"]["servername"] == "test-server"
        assert post_signal["kwargs"]["filename"] == "test_backup.sql"
        assert "storage" in post_signal["kwargs"]

        signals.post_backup.disconnect(self.signal_receiver)

    def test_pre_restore_signal_sent(self):
        """Test that pre_restore signal is sent before database restore."""
        signals.pre_restore.connect(self.signal_receiver)

        command = DbRestoreCommand()
        command.storage = get_storage()
        command.servername = "test-server"
        command.database = {"NAME": "test_db"}
        command.database_name = "test_db"
        command.path = None
        command.decrypt = False
        command.uncompress = False
        command.interactive = False
        command.logger = Mock()
        command.schemas = []
        command.no_drop = False
        command.pg_options = ""

        # Mock the methods to avoid actual operations
        mock_file = Mock()
        mock_file.size = 1024
        mock_file.seek = Mock()
        mock_file.tell = Mock(return_value=1024)
        mock_file.fileno = Mock(return_value=1)  # Mock fileno support
        command._get_backup_file = Mock(return_value=("test_backup.sql", mock_file))
        command.connector = Mock()

        with patch("dbbackup.management.commands.dbrestore.get_connector") as mock_get_connector:
            mock_get_connector.return_value = command.connector

            command._restore_backup()

        # Verify pre_restore signal was sent
        assert len(self.received_signals) >= 1
        pre_signal = self.received_signals[0]
        assert pre_signal["sender"] == DbRestoreCommand
        assert pre_signal["kwargs"]["database"] == command.database
        assert pre_signal["kwargs"]["database_name"] == "test_db"
        assert pre_signal["kwargs"]["filename"] == "test_backup.sql"
        assert pre_signal["kwargs"]["servername"] == "test-server"

        signals.pre_restore.disconnect(self.signal_receiver)

    def test_post_restore_signal_sent(self):
        """Test that post_restore signal is sent after database restore."""
        signals.post_restore.connect(self.signal_receiver)

        command = DbRestoreCommand()
        command.storage = get_storage()
        command.servername = "test-server"
        command.database = {"NAME": "test_db"}
        command.database_name = "test_db"
        command.path = None
        command.decrypt = False
        command.uncompress = False
        command.interactive = False
        command.logger = Mock()
        command.schemas = []
        command.no_drop = False
        command.pg_options = ""

        # Mock the methods to avoid actual operations
        mock_file = Mock()
        mock_file.size = 1024
        mock_file.seek = Mock()
        mock_file.tell = Mock(return_value=1024)
        mock_file.fileno = Mock(return_value=1)  # Mock fileno support
        command._get_backup_file = Mock(return_value=("test_backup.sql", mock_file))
        command.connector = Mock()

        with patch("dbbackup.management.commands.dbrestore.get_connector") as mock_get_connector:
            mock_get_connector.return_value = command.connector

            command._restore_backup()

        # Verify post_restore signal was sent
        assert len(self.received_signals) >= 1
        post_signal = self.received_signals[-1]
        assert post_signal["sender"] == DbRestoreCommand
        assert post_signal["kwargs"]["database"] == command.database
        assert post_signal["kwargs"]["database_name"] == "test_db"
        assert post_signal["kwargs"]["filename"] == "test_backup.sql"
        assert post_signal["kwargs"]["servername"] == "test-server"
        assert post_signal["kwargs"]["connector"] == command.connector

        signals.post_restore.disconnect(self.signal_receiver)

    def test_pre_media_backup_signal_sent(self):
        """Test that pre_media_backup signal is sent before media backup."""
        signals.pre_media_backup.connect(self.signal_receiver)

        command = MediaBackupCommand()
        command.storage = get_storage()
        command.servername = "test-server"
        command.filename = None
        command.path = None
        command.compress = False
        command.encrypt = False
        command.logger = Mock()
        command.content_type = "media"

        # Mock the methods to avoid actual operations
        mock_file = Mock()
        mock_file.size = 1024
        mock_file.seek = Mock()
        mock_file.tell = Mock(return_value=1024)
        command._create_tar = Mock(return_value=mock_file)
        command.write_to_storage = Mock()
        command.write_local_file = Mock()

        command.backup_mediafiles()

        # Verify pre_media_backup signal was sent
        assert len(self.received_signals) >= 1
        pre_signal = self.received_signals[0]
        assert pre_signal["sender"] == MediaBackupCommand
        assert pre_signal["kwargs"]["servername"] == "test-server"
        assert "storage" in pre_signal["kwargs"]

        signals.pre_media_backup.disconnect(self.signal_receiver)

    def test_post_media_backup_signal_sent(self):
        """Test that post_media_backup signal is sent after media backup."""
        signals.post_media_backup.connect(self.signal_receiver)

        command = MediaBackupCommand()
        command.storage = get_storage()
        command.servername = "test-server"
        command.filename = None
        command.path = None
        command.compress = False
        command.encrypt = False
        command.logger = Mock()
        command.content_type = "media"

        # Mock the methods to avoid actual operations
        mock_file = Mock()
        mock_file.size = 1024
        mock_file.seek = Mock()
        mock_file.tell = Mock(return_value=1024)
        command._create_tar = Mock(return_value=mock_file)
        command.write_to_storage = Mock()
        command.write_local_file = Mock()

        command.backup_mediafiles()

        # Verify post_media_backup signal was sent
        assert len(self.received_signals) >= 1
        post_signal = self.received_signals[-1]
        assert post_signal["sender"] == MediaBackupCommand
        assert post_signal["kwargs"]["servername"] == "test-server"
        assert "filename" in post_signal["kwargs"]
        assert "storage" in post_signal["kwargs"]

        signals.post_media_backup.disconnect(self.signal_receiver)

    def test_pre_media_restore_signal_sent(self):
        """Test that pre_media_restore signal is sent before media restore."""
        signals.pre_media_restore.connect(self.signal_receiver)

        command = MediaRestoreCommand()
        command.storage = get_storage()
        command.servername = "test-server"
        command.decrypt = False
        command.uncompress = False
        command.interactive = False
        command.logger = Mock()

        # Mock the methods to avoid actual operations
        mock_file = Mock()
        mock_file.size = 1024
        mock_file.seek = Mock()
        mock_file.tell = Mock(return_value=1024)
        command._get_backup_file = Mock(return_value=("test_media.tar", mock_file))
        command._upload_file = Mock()

        with patch("tarfile.open") as mock_tarfile_open:
            mock_tar = Mock()
            mock_tar.__iter__ = Mock(return_value=iter([]))
            mock_tarfile_open.return_value = mock_tar

            command._restore_backup()

        # Verify pre_media_restore signal was sent
        assert len(self.received_signals) >= 1
        pre_signal = self.received_signals[0]
        assert pre_signal["sender"] == MediaRestoreCommand
        assert pre_signal["kwargs"]["filename"] == "test_media.tar"
        assert pre_signal["kwargs"]["servername"] == "test-server"
        assert "storage" in pre_signal["kwargs"]

        signals.pre_media_restore.disconnect(self.signal_receiver)

    def test_post_media_restore_signal_sent(self):
        """Test that post_media_restore signal is sent after media restore."""
        signals.post_media_restore.connect(self.signal_receiver)

        command = MediaRestoreCommand()
        command.storage = get_storage()
        command.servername = "test-server"
        command.decrypt = False
        command.uncompress = False
        command.interactive = False
        command.logger = Mock()

        # Mock the methods to avoid actual operations
        mock_file = Mock()
        mock_file.size = 1024
        mock_file.seek = Mock()
        mock_file.tell = Mock(return_value=1024)
        command._get_backup_file = Mock(return_value=("test_media.tar", mock_file))
        command._upload_file = Mock()

        with patch("tarfile.open") as mock_tarfile_open:
            mock_tar = Mock()
            mock_tar.__iter__ = Mock(return_value=iter([]))
            mock_tarfile_open.return_value = mock_tar

            command._restore_backup()

        # Verify post_media_restore signal was sent
        assert len(self.received_signals) >= 1
        post_signal = self.received_signals[-1]
        assert post_signal["sender"] == MediaRestoreCommand
        assert post_signal["kwargs"]["filename"] == "test_media.tar"
        assert post_signal["kwargs"]["servername"] == "test-server"
        assert "storage" in post_signal["kwargs"]

        signals.post_media_restore.disconnect(self.signal_receiver)

    def test_all_signals_defined(self):
        """Test that all expected signals are defined in the signals module."""
        expected_signals = [
            "pre_backup",
            "post_backup",
            "pre_restore",
            "post_restore",
            "pre_media_backup",
            "post_media_backup",
            "pre_media_restore",
            "post_media_restore",
        ]

        for signal_name in expected_signals:
            assert hasattr(signals, signal_name), f"Signal '{signal_name}' is not defined in signals module"
            signal = getattr(signals, signal_name)
            assert hasattr(signal, "send"), f"Signal '{signal_name}' does not have a send method"
