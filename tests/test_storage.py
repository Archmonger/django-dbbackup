from unittest.mock import patch

import pytest
from django.test import TestCase

from dbbackup import utils
from dbbackup.storage import Storage, get_storage, get_storage_class
from tests.utils import HANDLED_FILES, FakeStorage

DEFAULT_STORAGE_PATH = "django.core.files.storage.FileSystemStorage"
STORAGE_OPTIONS = {"location": "tmp"}


class GetStorageTest(TestCase):
    @patch("dbbackup.settings.STORAGE", DEFAULT_STORAGE_PATH)
    @patch("dbbackup.settings.STORAGE_OPTIONS", STORAGE_OPTIONS)
    def test_func(self, *args):
        assert isinstance(get_storage(), Storage)

    def test_set_path(self):
        fake_storage_path = "tests.utils.FakeStorage"
        storage = get_storage(fake_storage_path)
        assert isinstance(storage.storage, FakeStorage)

    @patch("dbbackup.settings.STORAGE", DEFAULT_STORAGE_PATH)
    def test_set_options(self, *args):
        storage = get_storage(options=STORAGE_OPTIONS)
        assert storage.storage.__module__ in {"django.core.files.storage.filesystem"}

    def test_get_storage_class(self):
        storage_class = get_storage_class(DEFAULT_STORAGE_PATH)
        assert storage_class.__module__ in {"django.core.files.storage.filesystem"}
        assert storage_class.__name__ in ("FileSystemStorage", "DefaultStorage")

        storage_class = get_storage_class("tests.utils.FakeStorage")
        assert storage_class.__module__ == "tests.utils"
        assert storage_class.__name__ == "FakeStorage"

    def test_default_storage_class(self):
        storage_class = get_storage_class()
        assert storage_class.__module__ in {"django.core.files.storage"}
        assert storage_class.__name__ in ("FileSystemStorage", "DefaultStorage")

    def test_invalid_storage_class_path(self):
        with pytest.raises(ImportError):
            get_storage_class("invalid.path.to.StorageClass")

    def test_storages_settings(self):
        from .settings import STORAGES

        assert isinstance(STORAGES, dict)
        assert STORAGES["dbbackup"]["BACKEND"] == "tests.utils.FakeStorage"

        from dbbackup.settings import DJANGO_STORAGES, STORAGE

        assert isinstance(DJANGO_STORAGES, dict)
        assert DJANGO_STORAGES == STORAGES
        assert STORAGES["dbbackup"]["BACKEND"] == STORAGE

        storage = get_storage()
        assert storage.storage.__class__.__module__ == "tests.utils"
        assert storage.storage.__class__.__name__ == "FakeStorage"

    def test_storages_settings_options(self):
        from dbbackup.settings import STORAGE_OPTIONS

        from .settings import STORAGES

        assert STORAGES["dbbackup"]["OPTIONS"] == STORAGE_OPTIONS


class StorageTest(TestCase):
    def setUp(self):
        self.storageCls = Storage
        self.storageCls.name = "foo"
        self.storage = Storage()


class StorageListBackupsTest(TestCase):
    def setUp(self):
        HANDLED_FILES.clean()
        self.storage = get_storage()
        # foodb files
        HANDLED_FILES["written_files"] += [
            (utils.filename_generate(ext, "foodb"), None) for ext in ("db", "db.gz", "db.gpg", "db.gz.gpg")
        ]
        HANDLED_FILES["written_files"] += [
            (utils.filename_generate(ext, "hamdb", "fooserver"), None) for ext in ("db", "db.gz", "db.gpg", "db.gz.gpg")
        ]
        # Media file
        HANDLED_FILES["written_files"] += [
            (utils.filename_generate(ext, None, None, "media"), None)
            for ext in ("tar", "tar.gz", "tar.gpg", "tar.gz.gpg")
        ]
        HANDLED_FILES["written_files"] += [
            (utils.filename_generate(ext, "bardb", "barserver"), None) for ext in ("db", "db.gz", "db.gpg", "db.gz.gpg")
        ]
        # barserver files
        HANDLED_FILES["written_files"] += [("file_without_date", None)]

    def test_nofilter(self):
        files = self.storage.list_backups()
        assert len(HANDLED_FILES["written_files"]) - 1 == len(files)
        for file in files:
            assert file != "file_without_date"

    def test_encrypted(self):
        files = self.storage.list_backups(encrypted=True)
        for file in files:
            assert ".gpg" in file

    def test_compressed(self):
        files = self.storage.list_backups(compressed=True)
        for file in files:
            assert ".gz" in file

    def test_not_encrypted(self):
        files = self.storage.list_backups(encrypted=False)
        for file in files:
            assert ".gpg" not in file

    def test_not_compressed(self):
        files = self.storage.list_backups(compressed=False)
        for file in files:
            assert ".gz" not in file

    def test_content_type_db(self):
        files = self.storage.list_backups(content_type="db")
        for file in files:
            assert ".db" in file

    def test_database(self):
        files = self.storage.list_backups(database="foodb")
        for file in files:
            assert "foodb" in file
            assert "bardb" not in file
            assert "hamdb" not in file

    def test_servername(self):
        files = self.storage.list_backups(servername="fooserver")
        for file in files:
            assert "fooserver" in file
            assert "barserver" not in file
        files = self.storage.list_backups(servername="barserver")
        for file in files:
            assert "barserver" in file
            assert "fooserver" not in file

    def test_content_type_media(self):
        files = self.storage.list_backups(content_type="media")
        for file in files:
            assert ".tar" in file


class StorageGetLatestTest(TestCase):
    def setUp(self):
        self.storage = get_storage()
        HANDLED_FILES["written_files"] = [
            (f, None)
            for f in [
                "2015-02-06-042810.bak",
                "2015-02-07-042810.bak",
                "2015-02-08-042810.bak",
            ]
        ]

    def tearDown(self):
        HANDLED_FILES.clean()

    def test_func(self):
        filename = self.storage.get_latest_backup()
        assert filename == "2015-02-08-042810.bak"


class StorageGetMostRecentTest(TestCase):
    def setUp(self):
        self.storage = get_storage()
        HANDLED_FILES["written_files"] = [
            (f, None)
            for f in [
                "2015-02-06-042810.bak",
                "2015-02-07-042810.bak",
                "2015-02-08-042810.bak",
            ]
        ]

    def tearDown(self):
        HANDLED_FILES.clean()

    def test_func(self):
        filename = self.storage.get_older_backup()
        assert filename == "2015-02-06-042810.bak"


def keep_only_even_files(filename):
    from dbbackup.utils import filename_to_date

    return filename_to_date(filename).day % 2 == 0


class StorageCleanOldBackupsTest(TestCase):
    def setUp(self):
        self.storage = get_storage()
        HANDLED_FILES.clean()
        HANDLED_FILES["written_files"] = [
            (f, None)
            for f in [
                "2015-02-06-042810.bak",
                "2015-02-07-042810.bak",
                "2015-02-08-042810.bak",
            ]
        ]

    def test_func(self):
        self.storage.clean_old_backups(keep_number=1)
        assert len(HANDLED_FILES["deleted_files"]) == 2

    @patch("dbbackup.settings.CLEANUP_KEEP_FILTER", keep_only_even_files)
    def test_keep_filter(self):
        self.storage.clean_old_backups(keep_number=1)
        assert ["2015-02-07-042810.bak"] == HANDLED_FILES["deleted_files"]


class StorageEdgeCasesTest(TestCase):
    @patch("dbbackup.settings.STORAGE", "")
    def test_get_storage_empty_path(self):
        """Test get_storage with empty path raises ImproperlyConfigured"""
        from django.core.exceptions import ImproperlyConfigured

        with pytest.raises(ImproperlyConfigured):
            get_storage()

    def test_storage_str_method(self):
        """Test Storage.__str__ method"""
        storage = get_storage()
        str_repr = str(storage)
        assert str_repr.startswith("dbbackup-")

    @patch("django.core.files.storage.DefaultStorage", side_effect=ImportError())
    def test_get_storage_class_fallback(self, mock_default_storage):
        """Test get_storage_class fallback when DefaultStorage fails"""
        # This should test the except block in get_storage_class
        storage_class = get_storage_class()
        assert storage_class is not None

    def test_get_older_backup_file_not_found(self):
        """Test get_older_backup when no files are available"""
        from dbbackup.storage import StorageError

        storage = get_storage()
        HANDLED_FILES.clean()  # Ensure no backup files exist

        with pytest.raises(StorageError) as context:
            storage.get_older_backup()

        assert "There's no backup file available" in str(context)
