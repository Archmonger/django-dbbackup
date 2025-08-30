from unittest.mock import patch

from django.test import TestCase

try:
    from dbbackup import checks
    from dbbackup.apps import DbbackupConfig
except ImportError:
    checks = None


def foobar_func(*args, **kwargs):
    return "foo"


class ChecksTest(TestCase):
    def setUp(self):
        if checks is None:
            self.skipTest("Test framework has been released in Django 1.7")

    def test_check(self):
        assert not checks.check_settings(DbbackupConfig)

    @patch("dbbackup.checks.settings.HOSTNAME", "")
    def test_hostname_invalid(self):
        expected_errors = [checks.W001]
        errors = checks.check_settings(DbbackupConfig)
        assert expected_errors == errors

    @patch("dbbackup.checks.settings.STORAGE", "")
    def test_hostname_storage(self):
        expected_errors = [checks.W002]
        errors = checks.check_settings(DbbackupConfig)
        assert expected_errors == errors

    @patch("dbbackup.checks.settings.FILENAME_TEMPLATE", foobar_func)
    def test_filename_template_is_callable(self):
        assert not checks.check_settings(DbbackupConfig)

    @patch("dbbackup.checks.settings.FILENAME_TEMPLATE", "{datetime}.bak")
    def test_filename_template_is_string(self):
        assert not checks.check_settings(DbbackupConfig)

    @patch("dbbackup.checks.settings.FILENAME_TEMPLATE", "foo.bak")
    def test_filename_template_no_date(self):
        expected_errors = [checks.W003]
        errors = checks.check_settings(DbbackupConfig)
        assert expected_errors == errors

    @patch("dbbackup.checks.settings.MEDIA_FILENAME_TEMPLATE", foobar_func)
    def test_media_filename_template_is_callable(self):
        assert not checks.check_settings(DbbackupConfig)

    @patch("dbbackup.checks.settings.MEDIA_FILENAME_TEMPLATE", "{datetime}.bak")
    def test_media_filename_template_is_string(self):
        assert not checks.check_settings(DbbackupConfig)

    @patch("dbbackup.checks.settings.MEDIA_FILENAME_TEMPLATE", "foo.bak")
    def test_media_filename_template_no_date(self):
        expected_errors = [checks.W004]
        errors = checks.check_settings(DbbackupConfig)
        assert expected_errors == errors

    @patch("dbbackup.checks.settings.DATE_FORMAT", "foo@net.pt")
    def test_date_format_warning(self):
        expected_errors = [checks.W005]
        errors = checks.check_settings(DbbackupConfig)
        assert expected_errors == errors

    @patch("dbbackup.checks.settings.FILENAME_TEMPLATE", "foo/bar-{datetime}.ext")
    def test_db_filename_template_with_slash(self):
        expected_errors = [checks.W007]
        errors = checks.check_settings(DbbackupConfig)
        assert expected_errors == errors

    @patch("dbbackup.checks.settings.FILENAME_TEMPLATE", lambda _: "foo/bar")
    def test_db_filename_template_callable_with_slash(self):
        expected_errors = [checks.W007]
        errors = checks.check_settings(DbbackupConfig)
        assert expected_errors == errors

    @patch("dbbackup.checks.settings.MEDIA_FILENAME_TEMPLATE", "foo/bar-{datetime}.ext")
    def test_media_filename_template_with_slash(self):
        expected_errors = [checks.W008]
        errors = checks.check_settings(DbbackupConfig)
        assert expected_errors == errors

    @patch("dbbackup.checks.settings.MEDIA_FILENAME_TEMPLATE", lambda _: "foo/bar")
    def test_media_filename_template_callable_with_slash(self):
        expected_errors = [checks.W008]
        errors = checks.check_settings(DbbackupConfig)
        assert expected_errors == errors
