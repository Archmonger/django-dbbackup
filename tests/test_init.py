"""Tests for dbbackup.__init__ module."""

from django.test import TestCase


class InitModuleTest(TestCase):
    def test_version_defined(self):
        """Test that version is properly defined"""
        import dbbackup
        self.assertTrue(hasattr(dbbackup, "__version__"))
        self.assertIsInstance(dbbackup.__version__, str)