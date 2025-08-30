import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.management import execute_from_command_line
from django.test import TransactionTestCase as TestCase

from tests.testapp import models
from tests.utils import (
    HANDLED_FILES,
    TEST_DATABASE,
    add_private_gpg,
    add_public_gpg,
    clean_gpg_keys,
)

GPG_AVAILABLE = shutil.which("gpg") is not None


@unittest.skipIf(not GPG_AVAILABLE, "gpg executable not available")
class DbBackupCommandTest(TestCase):
    def setUp(self):
        HANDLED_FILES.clean()
        add_public_gpg()
        open(TEST_DATABASE["NAME"], "a").close()
        self.instance = models.CharModel.objects.create(field="foo")

    def tearDown(self):
        clean_gpg_keys()

    def test_database(self):
        argv = ["", "dbbackup", "--database=default"]
        execute_from_command_line(argv)
        assert len(HANDLED_FILES["written_files"]) == 1
        filename, outputfile = HANDLED_FILES["written_files"][0]
        # Test file content
        outputfile.seek(0)
        assert outputfile.read()

    def test_encrypt(self):
        argv = ["", "dbbackup", "--encrypt"]
        execute_from_command_line(argv)
        assert len(HANDLED_FILES["written_files"]) == 1
        filename, outputfile = HANDLED_FILES["written_files"][0]
        assert filename.endswith(".gpg")
        # Test file content
        outputfile = HANDLED_FILES["written_files"][0][1]
        outputfile.seek(0)
        assert outputfile.read().startswith(b"-----BEGIN PGP MESSAGE-----")

    def test_compress(self):
        argv = ["", "dbbackup", "--compress"]
        execute_from_command_line(argv)
        assert len(HANDLED_FILES["written_files"]) == 1
        filename, outputfile = HANDLED_FILES["written_files"][0]
        assert filename.endswith(".gz")

    def test_compress_and_encrypt(self):
        argv = ["", "dbbackup", "--compress", "--encrypt"]
        execute_from_command_line(argv)
        assert len(HANDLED_FILES["written_files"]) == 1
        filename, outputfile = HANDLED_FILES["written_files"][0]
        assert filename.endswith(".gz.gpg")
        # Test file content
        outputfile = HANDLED_FILES["written_files"][0][1]
        outputfile.seek(0)
        assert outputfile.read().startswith(b"-----BEGIN PGP MESSAGE-----")


@patch("dbbackup.management.commands._base.input", return_value="y")
@unittest.skipIf(not GPG_AVAILABLE, "gpg executable not available")
class DbRestoreCommandTest(TestCase):
    def setUp(self):
        HANDLED_FILES.clean()
        add_public_gpg()
        add_private_gpg()
        open(TEST_DATABASE["NAME"], "a").close()
        self.instance = models.CharModel.objects.create(field="foo")

    def tearDown(self):
        clean_gpg_keys()

    def test_restore(self, *args):
        # Create backup
        execute_from_command_line(["", "dbbackup"])
        self.instance.delete()
        # Restore
        execute_from_command_line(["", "dbrestore"])
        restored = models.CharModel.objects.all().exists()
        assert restored

    @patch("dbbackup.utils.getpass", return_value=None)
    def test_encrypted(self, *args):
        # Create backup
        execute_from_command_line(["", "dbbackup", "--encrypt"])
        self.instance.delete()
        # Restore
        execute_from_command_line(["", "dbrestore", "--decrypt"])
        restored = models.CharModel.objects.all().exists()
        assert restored

    def test_compressed(self, *args):
        # Create backup
        execute_from_command_line(["", "dbbackup", "--compress"])
        self.instance.delete()
        # Restore
        execute_from_command_line(["", "dbrestore", "--uncompress"])
        restored = models.CharModel.objects.all().exists()
        assert restored

    def test_no_backup_available(self, *args):
        with pytest.raises(SystemExit):
            execute_from_command_line(["", "dbrestore"])

    @patch("dbbackup.utils.getpass", return_value=None)
    def test_available_but_not_encrypted(self, *args):
        # Create backup
        execute_from_command_line(["", "dbbackup"])
        # Restore
        with pytest.raises(SystemExit):
            execute_from_command_line(["", "dbrestore", "--decrypt"])

    def test_available_but_not_compressed(self, *args):
        # Create backup
        execute_from_command_line(["", "dbbackup"])
        # Restore
        with pytest.raises(SystemExit):
            execute_from_command_line(["", "dbrestore", "--uncompress"])

    def test_specify_db(self, *args):
        # Create backup
        execute_from_command_line(["", "dbbackup", "--database", "default"])
        # Test wrong name
        with pytest.raises(SystemExit):
            execute_from_command_line(["", "dbrestore", "--database", "foo"])
        # Restore
        execute_from_command_line(["", "dbrestore", "--database", "default"])

    @patch("dbbackup.utils.getpass", return_value=None)
    def test_compressed_and_encrypted(self, *args):
        # Create backup
        execute_from_command_line(["", "dbbackup", "--compress", "--encrypt"])
        self.instance.delete()
        # Restore
        execute_from_command_line(["", "dbrestore", "--uncompress", "--decrypt"])
        restored = models.CharModel.objects.all().exists()
        assert restored


@unittest.skipIf(not GPG_AVAILABLE, "gpg executable not available")
class MediaBackupCommandTest(TestCase):
    def setUp(self):
        HANDLED_FILES.clean()
        add_public_gpg()

    def tearDown(self):
        clean_gpg_keys()

    def test_encrypt(self):
        argv = ["", "mediabackup", "--encrypt"]
        execute_from_command_line(argv)
        assert len(HANDLED_FILES["written_files"]) == 1
        filename, outputfile = HANDLED_FILES["written_files"][0]
        assert ".gpg" in filename
        # Test file content
        outputfile = HANDLED_FILES["written_files"][0][1]
        outputfile.seek(0)
        assert outputfile.read().startswith(b"-----BEGIN PGP MESSAGE-----")

    def test_compress(self):
        argv = ["", "mediabackup", "--compress"]
        execute_from_command_line(argv)
        assert len(HANDLED_FILES["written_files"]) == 1
        filename, outputfile = HANDLED_FILES["written_files"][0]
        assert ".gz" in filename

    @patch("dbbackup.utils.getpass", return_value=None)
    def test_compress_and_encrypted(self, getpass_mock):
        argv = ["", "mediabackup", "--compress", "--encrypt"]
        execute_from_command_line(argv)
        assert len(HANDLED_FILES["written_files"]) == 1
        filename, outputfile = HANDLED_FILES["written_files"][0]
        assert ".gpg" in filename
        assert ".gz" in filename
        # Test file content
        outputfile = HANDLED_FILES["written_files"][0][1]
        outputfile.seek(0)
        assert outputfile.read().startswith(b"-----BEGIN PGP MESSAGE-----")


@patch("dbbackup.management.commands._base.input", return_value="y")
@unittest.skipIf(not GPG_AVAILABLE, "gpg executable not available")
class MediaRestoreCommandTest(TestCase):
    def setUp(self):
        HANDLED_FILES.clean()
        add_public_gpg()
        add_private_gpg()

    def tearDown(self):
        clean_gpg_keys()
        self._empty_media()

    def _create_file(self, name=None):
        name = name or tempfile._RandomNameSequence().next()
        path = os.path.join(settings.MEDIA_ROOT, name)
        with open(path, "a+b") as fd:
            fd.write(b"foo")

    def _empty_media(self):
        import shutil

        if os.path.exists(settings.MEDIA_ROOT):
            shutil.rmtree(settings.MEDIA_ROOT)
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    def _is_restored(self):
        return bool(os.listdir(settings.MEDIA_ROOT))

    def test_restore(self, *args):
        # Create backup
        self._create_file("foo")
        execute_from_command_line(["", "mediabackup"])
        self._empty_media()
        # Restore
        execute_from_command_line(["", "mediarestore"])
        assert self._is_restored()

    @patch("dbbackup.utils.getpass", return_value=None)
    def test_encrypted(self, *args):
        # Create backup
        self._create_file("foo")
        execute_from_command_line(["", "mediabackup", "--encrypt"])
        self._empty_media()
        # Restore
        execute_from_command_line(["", "mediarestore", "--decrypt"])
        assert self._is_restored()

    def test_compressed(self, *args):
        # Create backup
        self._create_file("foo")
        execute_from_command_line(["", "mediabackup", "--compress"])
        self._empty_media()
        # Restore
        execute_from_command_line(["", "mediarestore", "--uncompress"])
        assert self._is_restored()

    def test_no_backup_available(self, *args):
        with pytest.raises(SystemExit):
            execute_from_command_line(["", "mediarestore"])

    @patch("dbbackup.utils.getpass", return_value=None)
    def test_available_but_not_encrypted(self, *args):
        # Create backup
        execute_from_command_line(["", "mediabackup"])
        # Restore
        with pytest.raises(SystemExit):
            execute_from_command_line(["", "mediarestore", "--decrypt"])

    def test_available_but_not_compressed(self, *args):
        # Create backup
        execute_from_command_line(["", "mediabackup"])
        # Restore
        with pytest.raises(SystemExit):
            execute_from_command_line(["", "mediarestore", "--uncompress"])

    def test_restore_file_with_media_in_path(self, *args):
        """Test that files with 'media' in their path are restored correctly."""
        # Create a file with 'media' in the path - this was the bug
        media_subdir = os.path.join(settings.MEDIA_ROOT, "uploads", "media", "images")
        os.makedirs(media_subdir, exist_ok=True)
        test_file = os.path.join(media_subdir, "test.jpg")
        with open(test_file, "w") as f:
            f.write("test image content")

        # Create backup
        execute_from_command_line(["", "mediabackup"])

        # Remove the file and directory structure
        os.remove(test_file)
        shutil.rmtree(media_subdir)

        # Restore backup
        execute_from_command_line(["", "mediarestore"])

        # Verify file was restored to correct location (not corrupted path)
        assert os.path.exists(test_file), "File should be restored to original path with 'media' in it"

        # Verify content is correct
        with open(test_file) as f:
            assert f.read() == "test image content"
