"""Tests for dbbackup.settings module."""

from unittest.mock import patch

from django.test import TestCase, override_settings


class SettingsTest(TestCase):
    @override_settings(DBBACKUP_FAILURE_RECIPIENTS=["test@example.com"])
    def test_failure_recipients_fallback(self):
        """Test that ADMINS falls back to FAILURE_RECIPIENTS when set"""
        # Need to reload the settings module to trigger the fallback logic
        import importlib
        import dbbackup.settings
        
        # Reload the module to trigger the settings evaluation
        importlib.reload(dbbackup.settings)
        
        # Check that ADMINS is set to FAILURE_RECIPIENTS
        self.assertEqual(dbbackup.settings.ADMINS, ["test@example.com"])

    @override_settings(DBBACKUP_FAILURE_RECIPIENTS=None, DBBACKUP_ADMIN=["admin@example.com"])
    def test_admins_fallback_to_dbbackup_admin(self):
        """Test that ADMINS falls back to DBBACKUP_ADMIN when FAILURE_RECIPIENTS is None"""
        import importlib
        import dbbackup.settings
        
        # Reload the module to trigger the settings evaluation
        importlib.reload(dbbackup.settings)
        
        # Check that ADMINS is set to DBBACKUP_ADMIN
        self.assertEqual(dbbackup.settings.ADMINS, ["admin@example.com"])