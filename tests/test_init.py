"""Tests for dbbackup.__init__ module."""

from unittest.mock import patch

from django.test import TestCase


class InitModuleTest(TestCase):
    @patch("django.VERSION", (3, 1, 0, "final", 0))
    def test_default_app_config_for_old_django(self):
        """Test that default_app_config is set for Django < 3.2"""
        # Need to reload the module to trigger the version check
        import importlib
        import dbbackup
        
        with patch.dict("sys.modules"):
            # Remove the module from cache to force reload
            if "dbbackup" in importlib.sys.modules:
                del importlib.sys.modules["dbbackup"]
            
            # Import the module again which should trigger the version check
            import dbbackup as reloaded_dbbackup
            
            # Check that the attribute is set
            self.assertTrue(hasattr(reloaded_dbbackup, "default_app_config"))
            self.assertEqual(reloaded_dbbackup.default_app_config, "dbbackup.apps.DbbackupConfig")

    def test_version_defined(self):
        """Test that version is properly defined"""
        import dbbackup
        self.assertTrue(hasattr(dbbackup, "__version__"))
        self.assertIsInstance(dbbackup.__version__, str)