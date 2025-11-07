"""Tests for dbbackup.settings module."""

from django.test import TestCase, override_settings


class SettingsTest(TestCase):
    @override_settings(DBBACKUP_ADMIN=["admin@example.com"])
    def test_admins_setting(self):
        """Test that ADMINS is set to DBBACKUP_ADMIN"""
        import importlib

        import dbbackup.settings

        # Reload the module to trigger the settings evaluation
        importlib.reload(dbbackup.settings)

        # Check that ADMINS is set to DBBACKUP_ADMIN
        assert ["admin@example.com"] == dbbackup.settings.ADMINS

    def test_deprecated_dbbackup_storage_raises(self):
        """Importing dbbackup.settings raises if DBBACKUP_STORAGE is set."""
        import importlib
        import sys

        # Ensure we import a fresh module so the check executes
        original_settings = sys.modules["dbbackup.settings"]
        del sys.modules["dbbackup.settings"]

        try:
            with self.assertRaises(RuntimeError):
                with override_settings(DBBACKUP_STORAGE="some.storage.Backend"):
                    importlib.import_module("dbbackup.settings")
        finally:
            sys.modules["dbbackup.settings"] = original_settings

    def test_deprecated_dbbackup_storage_options_raises(self):
        """Importing dbbackup.settings raises if DBBACKUP_STORAGE_OPTIONS is set."""
        import importlib
        import sys

        # Ensure we import a fresh module so the check executes
        original_settings = sys.modules["dbbackup.settings"]
        del sys.modules["dbbackup.settings"]

        try:
            with self.assertRaises(RuntimeError):
                with override_settings(DBBACKUP_STORAGE_OPTIONS={"option": True}):
                    importlib.import_module("dbbackup.settings")
        finally:
            sys.modules["dbbackup.settings"] = original_settings
