import os

import django
from django.core.management import call_command


def pytest_configure():
    """Configure Django for pytest."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    django.setup()

    # Run migrations to ensure test database is set up properly
    call_command("migrate", verbosity=0, interactive=False)
