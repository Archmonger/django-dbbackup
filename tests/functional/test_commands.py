import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

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
        self.assertEqual(1, len(HANDLED_FILES["written_files"]))
        filename, outputfile = HANDLED_FILES["written_files"][0]
        # Test file content
        outputfile.seek(0)
        self.assertTrue(outputfile.read())

    def test_encrypt(self):
        argv = ["", "dbbackup", "--encrypt"]
        execute_from_command_line(argv)
        self.assertEqual(1, len(HANDLED_FILES["written_files"]))
        filename, outputfile = HANDLED_FILES["written_files"][0]
        self.assertTrue(filename.endswith(".gpg"))
        # Test file content
        outputfile = HANDLED_FILES["written_files"][0][1]
        outputfile.seek(0)
        self.assertTrue(outputfile.read().startswith(b"-----BEGIN PGP MESSAGE-----"))

    def test_compress(self):
        argv = ["", "dbbackup", "--compress"]
        execute_from_command_line(argv)
        self.assertEqual(1, len(HANDLED_FILES["written_files"]))
        filename, outputfile = HANDLED_FILES["written_files"][0]
        self.assertTrue(filename.endswith(".gz"))

    def test_compress_and_encrypt(self):
        argv = ["", "dbbackup", "--compress", "--encrypt"]
        execute_from_command_line(argv)
        self.assertEqual(1, len(HANDLED_FILES["written_files"]))
        filename, outputfile = HANDLED_FILES["written_files"][0]
        self.assertTrue(filename.endswith(".gz.gpg"))
        # Test file content
        outputfile = HANDLED_FILES["written_files"][0][1]
        outputfile.seek(0)
        self.assertTrue(outputfile.read().startswith(b"-----BEGIN PGP MESSAGE-----"))


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
        self.assertTrue(restored)

    @patch("dbbackup.utils.getpass", return_value=None)
    def test_encrypted(self, *args):
        # Create backup
        execute_from_command_line(["", "dbbackup", "--encrypt"])
        self.instance.delete()
        # Restore
        execute_from_command_line(["", "dbrestore", "--decrypt"])
        restored = models.CharModel.objects.all().exists()
        self.assertTrue(restored)

    def test_compressed(self, *args):
        # Create backup
        execute_from_command_line(["", "dbbackup", "--compress"])
        self.instance.delete()
        # Restore
        execute_from_command_line(["", "dbrestore", "--uncompress"])
        restored = models.CharModel.objects.all().exists()
        self.assertTrue(restored)

    def test_no_backup_available(self, *args):
        with self.assertRaises(SystemExit):
            execute_from_command_line(["", "dbrestore"])

    @patch("dbbackup.utils.getpass", return_value=None)
    def test_available_but_not_encrypted(self, *args):
        # Create backup
        execute_from_command_line(["", "dbbackup"])
        # Restore
        with self.assertRaises(SystemExit):
            execute_from_command_line(["", "dbrestore", "--decrypt"])

    def test_available_but_not_compressed(self, *args):
        # Create backup
        execute_from_command_line(["", "dbbackup"])
        # Restore
        with self.assertRaises(SystemExit):
            execute_from_command_line(["", "dbrestore", "--uncompress"])

    def test_specify_db(self, *args):
        # Create backup
        execute_from_command_line(["", "dbbackup", "--database", "default"])
        # Test wrong name
        with self.assertRaises(SystemExit):
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
        self.assertTrue(restored)


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
        self.assertEqual(1, len(HANDLED_FILES["written_files"]))
        filename, outputfile = HANDLED_FILES["written_files"][0]
        self.assertTrue(".gpg" in filename)
        # Test file content
        outputfile = HANDLED_FILES["written_files"][0][1]
        outputfile.seek(0)
        self.assertTrue(outputfile.read().startswith(b"-----BEGIN PGP MESSAGE-----"))

    def test_compress(self):
        argv = ["", "mediabackup", "--compress"]
        execute_from_command_line(argv)
        self.assertEqual(1, len(HANDLED_FILES["written_files"]))
        filename, outputfile = HANDLED_FILES["written_files"][0]
        self.assertTrue(".gz" in filename)

    @patch("dbbackup.utils.getpass", return_value=None)
    def test_compress_and_encrypted(self, getpass_mock):
        argv = ["", "mediabackup", "--compress", "--encrypt"]
        execute_from_command_line(argv)
        self.assertEqual(1, len(HANDLED_FILES["written_files"]))
        filename, outputfile = HANDLED_FILES["written_files"][0]
        self.assertTrue(".gpg" in filename)
        self.assertTrue(".gz" in filename)
        # Test file content
        outputfile = HANDLED_FILES["written_files"][0][1]
        outputfile.seek(0)
        self.assertTrue(outputfile.read().startswith(b"-----BEGIN PGP MESSAGE-----"))


@patch("dbbackup.management.commands._base.input", return_value="y")
@unittest.skipIf(not GPG_AVAILABLE, "gpg executable not available")
class MediaRestoreCommandTest(TestCase):
    def setUp(self):
        HANDLED_FILES.clean()
        add_public_gpg()
        add_private_gpg()

    def tearDown(self):
        clean_gpg_keys()
        self._emtpy_media()

    def _create_file(self, name=None):
        name = name or tempfile._RandomNameSequence().next()
        path = os.path.join(settings.MEDIA_ROOT, name)
        with open(path, "a+b") as fd:
            fd.write(b"foo")

    def _emtpy_media(self):
        for fi in os.listdir(settings.MEDIA_ROOT):
            os.remove(os.path.join(settings.MEDIA_ROOT, fi))

    def _is_restored(self):
        return bool(os.listdir(settings.MEDIA_ROOT))

    def test_restore(self, *args):
        # Create backup
        self._create_file("foo")
        execute_from_command_line(["", "mediabackup"])
        self._emtpy_media()
        # Restore
        execute_from_command_line(["", "mediarestore"])
        self.assertTrue(self._is_restored())

    @patch("dbbackup.utils.getpass", return_value=None)
    def test_encrypted(self, *args):
        # Create backup
        self._create_file("foo")
        execute_from_command_line(["", "mediabackup", "--encrypt"])
        self._emtpy_media()
        # Restore
        execute_from_command_line(["", "mediarestore", "--decrypt"])
        self.assertTrue(self._is_restored())

    def test_compressed(self, *args):
        # Create backup
        self._create_file("foo")
        execute_from_command_line(["", "mediabackup", "--compress"])
        self._emtpy_media()
        # Restore
        execute_from_command_line(["", "mediarestore", "--uncompress"])
        self.assertTrue(self._is_restored())

    def test_no_backup_available(self, *args):
        with self.assertRaises(SystemExit):
            execute_from_command_line(["", "mediarestore"])

    @patch("dbbackup.utils.getpass", return_value=None)
    def test_available_but_not_encrypted(self, *args):
        # Create backup
        execute_from_command_line(["", "mediabackup"])
        # Restore
        with self.assertRaises(SystemExit):
            execute_from_command_line(["", "mediarestore", "--decrypt"])

    def test_available_but_not_compressed(self, *args):
        # Create backup
        execute_from_command_line(["", "mediabackup"])
        # Restore
        with self.assertRaises(SystemExit):
            execute_from_command_line(["", "mediarestore", "--uncompress"])
