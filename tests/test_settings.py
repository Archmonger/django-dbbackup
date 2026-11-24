"""Tests for dbbackup.settings module."""

import pytest
from django.test import TestCase, override_settings


class SettingsTest(TestCase):
    def test_admins_setting(self):
        """Test that ADMINS is set to DBBACKUP_ADMINS"""
        import importlib

        import dbbackup.settings

        try:
            with override_settings(DBBACKUP_ADMINS=["admin@example.com"]):
                importlib.reload(dbbackup.settings)
                assert dbbackup.settings.ADMINS == ["admin@example.com"]
        finally:
            importlib.reload(dbbackup.settings)

    def test_admins_singular_alias_setting(self):
        """Test that the legacy DBBACKUP_ADMIN spelling is still honored."""
        import importlib

        import dbbackup.settings

        try:
            with override_settings(DBBACKUP_ADMIN=["alias@example.com"]):
                importlib.reload(dbbackup.settings)
                assert dbbackup.settings.ADMINS == ["alias@example.com"]
        finally:
            importlib.reload(dbbackup.settings)

    def test_admins_plural_setting_takes_precedence(self):
        """Test that DBBACKUP_ADMINS wins when both spellings are set."""
        import importlib

        import dbbackup.settings

        try:
            with override_settings(
                DBBACKUP_ADMINS=["admin@example.com"],
                DBBACKUP_ADMIN=["alias@example.com"],
            ):
                importlib.reload(dbbackup.settings)
                assert dbbackup.settings.ADMINS == ["admin@example.com"]
        finally:
            importlib.reload(dbbackup.settings)

    @override_settings(DBBACKUP_GPG_RECIPIENT="test@test", DBBACKUP_GPG_ALWAYS_TRUST=False)
    def test_gpg_always_trust_setting(self):
        """GPG_ALWAYS_TRUST is read from DBBACKUP_GPG_ALWAYS_TRUST"""
        import importlib

        import dbbackup.settings

        self.addCleanup(importlib.reload, dbbackup.settings)
        importlib.reload(dbbackup.settings)

        assert dbbackup.settings.GPG_RECIPIENT == "test@test"
        assert dbbackup.settings.GPG_ALWAYS_TRUST is False

    @override_settings(DBBACKUP_GPG_RECIPIENT=None, DBBACKUP_GPG_ALWAYS_TRUST=True)
    def test_gpg_always_trust_without_recipient(self):
        """GPG_ALWAYS_TRUST is not overwritten when no recipient is configured"""
        import importlib

        import dbbackup.settings

        self.addCleanup(importlib.reload, dbbackup.settings)
        importlib.reload(dbbackup.settings)

        assert dbbackup.settings.GPG_RECIPIENT is None
        assert dbbackup.settings.GPG_ALWAYS_TRUST is True

    @override_settings(DBBACKUP_GPG_RECIPIENT="test@test")
    def test_gpg_always_trust_defaults_to_false(self):
        """GPG_ALWAYS_TRUST defaults to False, even when a recipient is configured"""
        import importlib

        from django.conf import settings as django_settings

        import dbbackup.settings

        # Emulate a project that never set DBBACKUP_GPG_ALWAYS_TRUST
        del django_settings._wrapped.DBBACKUP_GPG_ALWAYS_TRUST
        self.addCleanup(importlib.reload, dbbackup.settings)
        importlib.reload(dbbackup.settings)

        assert dbbackup.settings.GPG_RECIPIENT == "test@test"
        assert dbbackup.settings.GPG_ALWAYS_TRUST is False

    def test_deprecated_dbbackup_storage_raises(self):
        """Importing dbbackup.settings raises if DBBACKUP_STORAGE is set."""
        import importlib
        import sys

        # Ensure we import a fresh module so the check executes
        original_settings = sys.modules["dbbackup.settings"]
        del sys.modules["dbbackup.settings"]

        try:
            with pytest.raises(RuntimeError), override_settings(DBBACKUP_STORAGE="some.storage.Backend"):
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
            with pytest.raises(RuntimeError), override_settings(DBBACKUP_STORAGE_OPTIONS={"option": True}):
                importlib.import_module("dbbackup.settings")
        finally:
            sys.modules["dbbackup.settings"] = original_settings
