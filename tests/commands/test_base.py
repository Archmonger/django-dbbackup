"""
Tests for base command class.
"""

import logging
import os
from io import BytesIO
from unittest.mock import patch

import pytest
from django.core.files import File
from django.test import TestCase

from dbbackup.management.commands._base import BaseDbBackupCommand
from dbbackup.storage import get_storage
from tests.utils import DEV_NULL, HANDLED_FILES


class BaseDbBackupCommandSetLoggerLevelTest(TestCase):
    def setUp(self):
        self.command = BaseDbBackupCommand()

    def test_0_level(self):
        self.command.verbosity = 0
        self.command._set_logger_level()
        assert self.command.logger.level == logging.WARNING

    def test_1_level(self):
        self.command.verbosity = 1
        self.command._set_logger_level()
        assert self.command.logger.level == logging.INFO

    def test_2_level(self):
        self.command.verbosity = 2
        self.command._set_logger_level()
        assert self.command.logger.level == logging.DEBUG

    def test_3_level(self):
        self.command.verbosity = 3
        self.command._set_logger_level()
        assert self.command.logger.level == logging.DEBUG

    def test_quiet(self):
        self.command.quiet = True
        self.command._set_logger_level()
        assert self.command.logger.level > logging.ERROR


class BaseDbBackupCommandMethodsTest(TestCase):
    def setUp(self):
        HANDLED_FILES.clean()
        self.command = BaseDbBackupCommand()
        self.command.storage = get_storage()

    def test_read_from_storage(self):
        HANDLED_FILES["written_files"].append(["foo", File(BytesIO(b"bar"))])
        file_ = self.command.read_from_storage("foo")
        assert file_.read() == b"bar"

    def test_write_to_storage(self):
        self.command.write_to_storage(BytesIO(b"foo"), "bar")
        assert HANDLED_FILES["written_files"][0][0] == "bar"

    def test_read_local_file(self):
        # setUp: use repository-local tmp directory
        local_tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tmp")
        os.makedirs(local_tmp, exist_ok=True)
        self.command.path = os.path.join(local_tmp, "foo.bak")
        open(self.command.path, "w").close()
        # Test
        self.command.read_local_file(self.command.path)
        # tearDown
        os.remove(self.command.path)

    def test_write_local_file(self):
        local_tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tmp")
        os.makedirs(local_tmp, exist_ok=True)
        fd, path = File(BytesIO(b"foo")), os.path.join(local_tmp, "foo.bak")
        self.command.write_local_file(fd, path)
        assert os.path.exists(path)
        # tearDown
        os.remove(path)

    def test_ask_confirmation(self):
        # Yes
        with patch("dbbackup.management.commands._base.input", return_value="y"):
            self.command._ask_confirmation()
        with patch("dbbackup.management.commands._base.input", return_value="Y"):
            self.command._ask_confirmation()
        with patch("dbbackup.management.commands._base.input", return_value=""):
            self.command._ask_confirmation()
        with patch("dbbackup.management.commands._base.input", return_value="foo"):
            self.command._ask_confirmation()
        # No
        with patch("dbbackup.management.commands._base.input", return_value="n"), pytest.raises(SystemExit):
            self.command._ask_confirmation()
        with patch("dbbackup.management.commands._base.input", return_value="N"), pytest.raises(SystemExit):
            self.command._ask_confirmation()
        with patch("dbbackup.management.commands._base.input", return_value="No"), pytest.raises(SystemExit):
            self.command._ask_confirmation()


class BaseDbBackupCommandCleanupOldBackupsTest(TestCase):
    def setUp(self):
        HANDLED_FILES.clean()
        self.command = BaseDbBackupCommand()
        self.command.stdout = DEV_NULL
        self.command.encrypt = False
        self.command.compress = False
        self.command.servername = "foo-server"
        self.command.storage = get_storage()
        HANDLED_FILES["written_files"] = [
            (f, None)
            for f in [
                "fooserver-2015-02-06-042810.tar",
                "fooserver-2015-02-07-042810.tar",
                "fooserver-2015-02-08-042810.tar",
                "foodb-fooserver-2015-02-06-042810.dump",
                "foodb-fooserver-2015-02-07-042810.dump",
                "foodb-fooserver-2015-02-08-042810.dump",
                "bardb-fooserver-2015-02-06-042810.dump",
                "bardb-fooserver-2015-02-07-042810.dump",
                "bardb-fooserver-2015-02-08-042810.dump",
                "hamdb-hamserver-2015-02-06-042810.dump",
                "hamdb-hamserver-2015-02-07-042810.dump",
                "hamdb-hamserver-2015-02-08-042810.dump",
            ]
        ]

    @patch("dbbackup.settings.CLEANUP_KEEP", 1)
    def test_clean_db(self):
        self.command.content_type = "db"
        self.command.database = "foodb"
        self.command._cleanup_old_backups(database="foodb")
        assert len(HANDLED_FILES["deleted_files"]) == 2
        assert "foodb-fooserver-2015-02-08-042810.dump" not in HANDLED_FILES["deleted_files"]

    @patch("dbbackup.settings.CLEANUP_KEEP", 1)
    def test_clean_other_db(self):
        self.command.content_type = "db"
        self.command._cleanup_old_backups(database="bardb")
        assert len(HANDLED_FILES["deleted_files"]) == 2
        assert "bardb-fooserver-2015-02-08-042810.dump" not in HANDLED_FILES["deleted_files"]

    @patch("dbbackup.settings.CLEANUP_KEEP", 1)
    def test_clean_other_server_db(self):
        self.command.content_type = "db"
        self.command._cleanup_old_backups(database="bardb")
        assert len(HANDLED_FILES["deleted_files"]) == 2
        assert "bardb-fooserver-2015-02-08-042810.dump" not in HANDLED_FILES["deleted_files"]

    @patch("dbbackup.settings.CLEANUP_KEEP_MEDIA", 1)
    def test_clean_media(self):
        self.command.content_type = "media"
        self.command._cleanup_old_backups()
        assert len(HANDLED_FILES["deleted_files"]) == 2
        assert "foo-server-2015-02-08-042810.tar" not in HANDLED_FILES["deleted_files"]
