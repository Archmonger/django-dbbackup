"""
Tests for mediabackup command.
"""

import contextlib
import os
import shutil
import tempfile

GPG_AVAILABLE = shutil.which("gpg") is not None

from django.test import TestCase

from dbbackup.management.commands.mediabackup import Command as DbbackupCommand
from dbbackup.storage import get_storage, get_storage_class
from tests.utils import DEV_NULL, HANDLED_FILES, add_public_gpg


class MediabackupBackupMediafilesTest(TestCase):
    def setUp(self):
        HANDLED_FILES.clean()
        self.command = DbbackupCommand()
        self.command.servername = "foo-server"
        self.command.storage = get_storage()
        self.command.stdout = DEV_NULL
        self.command.compress = False
        self.command.encrypt = False
        self.command.path = None
        self.command.media_storage = get_storage_class()()
        self.command.filename = None

    def tearDown(self):
        if self.command.path is not None:
            with contextlib.suppress(OSError):
                os.remove(self.command.path)

    def test_func(self):
        self.command.backup_mediafiles()
        self.assertEqual(1, len(HANDLED_FILES["written_files"]))

    def test_compress(self):
        self.command.compress = True
        self.command.backup_mediafiles()
        self.assertEqual(1, len(HANDLED_FILES["written_files"]))
        self.assertTrue(HANDLED_FILES["written_files"][0][0].endswith(".gz"))

    def test_encrypt(self):
        if not GPG_AVAILABLE:
            self.skipTest("gpg executable not available")
        self.command.encrypt = True
        add_public_gpg()
        self.command.backup_mediafiles()
        self.assertEqual(1, len(HANDLED_FILES["written_files"]))
        outputfile = HANDLED_FILES["written_files"][0][1]
        outputfile.seek(0)
        self.assertTrue(outputfile.read().startswith(b"-----BEGIN PGP MESSAGE-----"))

    def test_compress_and_encrypt(self):
        if not GPG_AVAILABLE:
            self.skipTest("gpg executable not available")
        self.command.compress = True
        self.command.encrypt = True
        add_public_gpg()
        self.command.backup_mediafiles()
        self.assertEqual(1, len(HANDLED_FILES["written_files"]))
        outputfile = HANDLED_FILES["written_files"][0][1]
        outputfile.seek(0)
        self.assertTrue(outputfile.read().startswith(b"-----BEGIN PGP MESSAGE-----"))

    def test_write_local_file(self):
        self.command.path = tempfile.mktemp()
        self.command.backup_mediafiles()
        self.assertTrue(os.path.exists(self.command.path))
        self.assertEqual(0, len(HANDLED_FILES["written_files"]))

    def test_output_filename(self):
        self.command.filename = "my_new_name.tar"
        self.command.backup_mediafiles()
        self.assertEqual(HANDLED_FILES["written_files"][0][0], self.command.filename)

    def test_s3_uri_output_path(self):
        """Test that S3 URIs in output path are handled correctly for mediabackup."""
        from unittest.mock import patch
        
        with patch("dbbackup.management.commands._base.BaseDbBackupCommand.write_to_storage") as mock_write_to_storage:
            self.command.path = "s3://mybucket/media/backup.tar"
            self.command.backup_mediafiles()
            
            # Verify write_to_storage was called with the S3 path
            self.assertTrue(mock_write_to_storage.called)
            args, kwargs = mock_write_to_storage.call_args
            self.assertEqual(args[1], "s3://mybucket/media/backup.tar")
            
            # Verify no files were written to local storage
            self.assertEqual(0, len(HANDLED_FILES["written_files"]))
