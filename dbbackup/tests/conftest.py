import os
import django

def pytest_configure():
    """Configure Django for pytest."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dbbackup.tests.settings")
    django.setup()
