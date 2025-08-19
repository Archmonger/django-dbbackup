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
        self.assertEqual(dbbackup.settings.ADMINS, ["admin@example.com"])