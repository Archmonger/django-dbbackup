import os

import django
import pytest
from django.core.management import call_command


def pytest_configure():
    """Configure Django for pytest."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    django.setup()

    # Run migrations to ensure test database is set up properly
    call_command("migrate", verbosity=0, interactive=False)


@pytest.fixture(autouse=True)
def restore_dbbackup_settings():
    """
    Undo ``importlib.reload(dbbackup.settings)`` between tests.

    Tests that need a new value in dbbackup.settings use override_settings plus a reload,
    but the reload mutates the module in place and most of them never reload again after
    the override is lifted, so the overridden value stayed visible to every test running
    afterwards in the same session.
    """
    from dbbackup import settings as dbbackup_settings

    snapshot = vars(dbbackup_settings).copy()
    yield
    namespace = vars(dbbackup_settings)
    namespace.clear()
    namespace.update(snapshot)
