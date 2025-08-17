from unittest.mock import patch

from django.test import TestCase

from dbbackup import utils
from dbbackup.storage import Storage, get_storage, get_storage_class
from tests.utils import HANDLED_FILES, FakeStorage

DEFAULT_STORAGE_PATH = "django.core.files.storage.FileSystemStorage"
STORAGE_OPTIONS = {"location": "tmp"}


class Get_StorageTest(TestCase):
    @patch("dbbackup.settings.STORAGE", DEFAULT_STORAGE_PATH)
    @patch("dbbackup.settings.STORAGE_OPTIONS", STORAGE_OPTIONS)
    def test_func(self, *args):
        self.assertIsInstance(get_storage(), Storage)

    def test_set_path(self):
        fake_storage_path = "tests.utils.FakeStorage"
        storage = get_storage(fake_storage_path)
        self.assertIsInstance(storage.storage, FakeStorage)

    @patch("dbbackup.settings.STORAGE", DEFAULT_STORAGE_PATH)
    def test_set_options(self, *args):
        storage = get_storage(options=STORAGE_OPTIONS)
        self.assertIn(
            storage.storage.__module__,
            {"django.core.files.storage.filesystem"},
        )

    def test_get_storage_class(self):
        storage_class = get_storage_class(DEFAULT_STORAGE_PATH)
        self.assertIn(
            storage_class.__module__,
            {"django.core.files.storage.filesystem"},
        )
        self.assertIn(storage_class.__name__, ("FileSystemStorage", "DefaultStorage"))

        storage_class = get_storage_class("tests.utils.FakeStorage")
        self.assertEqual(storage_class.__module__, "tests.utils")
        self.assertEqual(storage_class.__name__, "FakeStorage")

    def test_default_storage_class(self):
        storage_class = get_storage_class()
        self.assertIn(
            storage_class.__module__,
            {"django.core.files.storage"},
        )
        self.assertIn(storage_class.__name__, ("FileSystemStorage", "DefaultStorage"))

    def test_invalid_storage_class_path(self):
        with self.assertRaises(ImportError):
            get_storage_class("invalid.path.to.StorageClass")

    def test_storages_settings(self):
        from .settings import STORAGES

        self.assertIsInstance(STORAGES, dict)
        self.assertEqual(STORAGES["dbbackup"]["BACKEND"], "tests.utils.FakeStorage")

        from dbbackup.settings import DJANGO_STORAGES, STORAGE

        self.assertIsInstance(DJANGO_STORAGES, dict)
        self.assertEqual(DJANGO_STORAGES, STORAGES)
        self.assertEqual(STORAGES["dbbackup"]["BACKEND"], STORAGE)

        storage = get_storage()
        self.assertEqual(storage.storage.__class__.__module__, "tests.utils")
        self.assertEqual(storage.storage.__class__.__name__, "FakeStorage")

    def test_storages_settings_options(self):
        from dbbackup.settings import STORAGE_OPTIONS

        from .settings import STORAGES

        self.assertEqual(STORAGES["dbbackup"]["OPTIONS"], STORAGE_OPTIONS)


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
        self.assertEqual(len(HANDLED_FILES["written_files"]) - 1, len(files))
        for file in files:
            self.assertNotEqual("file_without_date", file)

    def test_encrypted(self):
        files = self.storage.list_backups(encrypted=True)
        for file in files:
            self.assertIn(".gpg", file)

    def test_compressed(self):
        files = self.storage.list_backups(compressed=True)
        for file in files:
            self.assertIn(".gz", file)

    def test_not_encrypted(self):
        files = self.storage.list_backups(encrypted=False)
        for file in files:
            self.assertNotIn(".gpg", file)

    def test_not_compressed(self):
        files = self.storage.list_backups(compressed=False)
        for file in files:
            self.assertNotIn(".gz", file)

    def test_content_type_db(self):
        files = self.storage.list_backups(content_type="db")
        for file in files:
            self.assertIn(".db", file)

    def test_database(self):
        files = self.storage.list_backups(database="foodb")
        for file in files:
            self.assertIn("foodb", file)
            self.assertNotIn("bardb", file)
            self.assertNotIn("hamdb", file)

    def test_servername(self):
        files = self.storage.list_backups(servername="fooserver")
        for file in files:
            self.assertIn("fooserver", file)
            self.assertNotIn("barserver", file)
        files = self.storage.list_backups(servername="barserver")
        for file in files:
            self.assertIn("barserver", file)
            self.assertNotIn("fooserver", file)

    def test_content_type_media(self):
        files = self.storage.list_backups(content_type="media")
        for file in files:
            self.assertIn(".tar", file)

    # def test_servername(self):
    #     files = self.storage.list_backups(servername='barserver')
    #     for file in files:
    #         self.assertIn('barserver', file)


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
        self.assertEqual(filename, "2015-02-08-042810.bak")


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
        self.assertEqual(filename, "2015-02-06-042810.bak")


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
        self.assertEqual(2, len(HANDLED_FILES["deleted_files"]))

    @patch("dbbackup.settings.CLEANUP_KEEP_FILTER", keep_only_even_files)
    def test_keep_filter(self):
        self.storage.clean_old_backups(keep_number=1)
        self.assertListEqual(["2015-02-07-042810.bak"], HANDLED_FILES["deleted_files"])
