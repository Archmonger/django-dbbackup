from io import StringIO
from unittest.mock import patch

from django.core.management import execute_from_command_line
from django.test import TestCase

from dbbackup.management.commands.listbackups import Command as ListbackupsCommand
from dbbackup.storage import get_storage
from tests.utils import HANDLED_FILES


class ListbackupsCommandTest(TestCase):
    def setUp(self):
        self.command = ListbackupsCommand()
        self.command.storage = get_storage()
        HANDLED_FILES["written_files"] = [
            (f, None)
            for f in [
                "2015-02-06-042810.bak",
                "2015-02-07-042810.bak",
                "2015-02-08-042810.bak",
            ]
        ]

    def test_get_backup_attrs(self):
        options = {}
        attrs = self.command.get_backup_attrs(options)
        self.assertEqual(len(HANDLED_FILES["written_files"]), len(attrs))


class ListbackupsCommandArgComputingTest(TestCase):
    def setUp(self):
        HANDLED_FILES["written_files"] = [
            (f, None)
            for f in [
                "2015-02-06-042810_foo.db",
                "2015-02-06-042810_foo.db.gz",
                "2015-02-06-042810_foo.db.gpg",
                "2015-02-06-042810_foo.db.gz.gpg",
                "2015-02-06-042810_foo.tar",
                "2015-02-06-042810_foo.tar.gz",
                "2015-02-06-042810_foo.tar.gpg",
                "2015-02-06-042810_foo.tar.gz.gpg",
                "2015-02-06-042810_bar.db",
                "2015-02-06-042810_bar.db.gz",
                "2015-02-06-042810_bar.db.gpg",
                "2015-02-06-042810_bar.db.gz.gpg",
                "2015-02-06-042810_bar.tar",
                "2015-02-06-042810_bar.tar.gz",
                "2015-02-06-042810_bar.tar.gpg",
                "2015-02-06-042810_bar.tar.gz.gpg",
            ]
        ]

    def test_list(self):
        execute_from_command_line(["", "listbackups"])

    def test_filter_encrypted(self):
        stdout = StringIO()
        with patch("sys.stdout", stdout):
            execute_from_command_line(["", "listbackups", "--encrypted", "-q"])
        stdout.seek(0)
        stdout.readline()
        for line in stdout.readlines():
            self.assertIn(".gpg", line)

    def test_filter_not_encrypted(self):
        stdout = StringIO()
        with patch("sys.stdout", stdout):
            execute_from_command_line(["", "listbackups", "--not-encrypted", "-q"])
        stdout.seek(0)
        stdout.readline()
        for line in stdout.readlines():
            self.assertNotIn(".gpg", line)

    def test_filter_compressed(self):
        stdout = StringIO()
        with patch("sys.stdout", stdout):
            execute_from_command_line(["", "listbackups", "--compressed", "-q"])
        stdout.seek(0)
        stdout.readline()
        for line in stdout.readlines():
            self.assertIn(".gz", line)

    def test_filter_not_compressed(self):
        stdout = StringIO()
        with patch("sys.stdout", stdout):
            execute_from_command_line(["", "listbackups", "--not-compressed", "-q"])
        stdout.seek(0)
        stdout.readline()
        for line in stdout.readlines():
            self.assertNotIn(".gz", line)

    def test_filter_db(self):
        stdout = StringIO()
        with patch("sys.stdout", stdout):
            execute_from_command_line(["", "listbackups", "--content-type", "db", "-q"])
        stdout.seek(0)
        stdout.readline()
        for line in stdout.readlines():
            self.assertIn(".db", line)

    def test_filter_media(self):
        stdout = StringIO()
        with patch("sys.stdout", stdout):
            execute_from_command_line(
                ["", "listbackups", "--content-type", "media", "-q"]
            )
        stdout.seek(0)
        stdout.readline()
        for line in stdout.readlines():
            self.assertIn(".tar", line)
