"""
Live PostgreSQL Testing Script for django-dbbackup

This script provides infrastructure for testing PostgreSQL backup/restore functionality
against a real PostgreSQL database. It complements the existing mocked tests by providing
end-to-end validation of the PostgreSQL connectors.

Usage:
    python scripts/postgres_live_test.py [--connector CONNECTOR] [--verbose]

Connectors:
    - PgDumpConnector (default): Uses pg_dump/psql for text-based SQL dumps
    - PgDumpBinaryConnector: Uses pg_dump/pg_restore for binary dumps
    - PgDumpGisConnector: Like PgDumpConnector but with PostGIS support
"""

import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from multiprocessing import Process
from pathlib import Path

# Add parent directory to path to import Django modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import django
from django.core.management import execute_from_command_line


class PostgreSQLTestRunner:
    """Manages a test database on the existing PostgreSQL instance."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.port = 5432  # Use default PostgreSQL port
        self.temp_dir = None
        self.test_db_name = f"dbbackup_test_{int(time.time())}"  # Unique DB name
        self.test_user = "postgres"  # Use postgres superuser
        self.test_password = None  # No password for local connection
        self.db_created = False

    def _log(self, message):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[PostgreSQL Test] {message}")

    def _run_command(self, cmd, check=True, use_sudo=False, **kwargs):
        """Run a command and optionally check for errors."""
        if use_sudo:
            if isinstance(cmd, list):
                cmd = ["sudo", "-u", "postgres"] + cmd
            else:
                cmd = f"sudo -u postgres {cmd}"
        self._log(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        result = subprocess.run(cmd, shell=isinstance(cmd, str), **kwargs)
        if check and result.returncode != 0:
            raise RuntimeError(f"Command failed with exit code {result.returncode}: {cmd}")
        return result

    def setup_postgres(self):
        """Set up a test database on the existing PostgreSQL instance."""

        if not shutil.which("pg_dump") or not shutil.which("psql"):
            install_instructions = ""
            if os.name == "posix":
                install_instructions = (
                    "\nInstall by running 'sudo apt install postgresql "
                    "postgresql-contrib postgresql-client-common postgresql-client'\n"
                    "... then run 'sudo service postgresql start' to start the server."
                )
            elif os.name == "nt":
                install_instructions = (
                    "\nInstall PostgreSQL from https://www.postgresql.org/download/windows/ "
                    "and ensure pg_dump and psql are in your PATH."
                )
            raise RuntimeError(f"PostgreSQL client tools (pg_dump, psql, etc) are not installed!{install_instructions}")

        self._log("Setting up test database...")
        self.temp_dir = tempfile.mkdtemp(prefix="dbbackup_postgres_")
        try:
            # Check if PostgreSQL is running
            self._log("Checking PostgreSQL connection...")
            self._run_command(["pg_isready", "-h", "localhost", "-p", str(self.port)], capture_output=True)
            self._log("PostgreSQL server is ready")

            # Create test database
            self._create_test_database()

        except Exception as e:
            self.cleanup()
            raise RuntimeError(f"Failed to set up PostgreSQL: {e}") from e

    def _create_test_database(self):
        """Create the test database."""
        self._log(f"Creating test database: {self.test_db_name}")

        # Create a test user with password
        test_user_password = "postgres"
        # Only create the user if it does not exist
        create_user_sql = (
            f"DO $$ BEGIN "
            f"IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{self.test_user}') THEN "
            f"CREATE USER {self.test_user} WITH PASSWORD '{test_user_password}' CREATEDB; "
            f"END IF; "
            f"END $$;"
        )

        # If user might already exists, continue
        with contextlib.suppress(RuntimeError):
            self._run_command(["psql", "-c", create_user_sql], capture_output=True, use_sudo=True)

        # Create database owned by the test user
        create_db_sql = f"CREATE DATABASE {self.test_db_name} OWNER {self.test_user};"
        self._run_command(["psql", "-c", create_db_sql], capture_output=True, use_sudo=True)

        # Update database config to use the test user
        self.test_user = f"{self.test_user}"
        self.test_password = test_user_password
        self.db_created = True

    def get_database_config(self):
        """Get Django database configuration for the test PostgreSQL instance."""
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": self.test_db_name,
            "USER": self.test_user,
            "PASSWORD": self.test_password,
            "HOST": "localhost",
            "PORT": self.port,
        }

    def cleanup(self):
        """Clean up the test database."""
        self._log("Cleaning up test database...")

        if self.db_created:
            try:
                # Drop the test database using psql with sudo
                drop_db_sql = f"DROP DATABASE IF EXISTS {self.test_db_name};"
                self._run_command(
                    ["psql", "-c", drop_db_sql], capture_output=True, check=False, use_sudo=True
                )  # Don't fail if database doesn't exist

                # Drop the test user
                drop_user_sql = f"DROP USER IF EXISTS {self.test_user};"
                self._run_command(["psql", "-c", drop_user_sql], capture_output=True, check=False, use_sudo=True)
            except Exception as e:
                self._log(f"Warning: Failed to drop test database or user: {e}")

        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil

            shutil.rmtree(self.temp_dir)


class PostgreSQLLiveTest:
    """Runs live tests against PostgreSQL connectors."""

    def __init__(self, connector_name="PgDumpConnector", verbose=False):
        self.connector_name = connector_name
        self.verbose = verbose
        self.postgres_runner = PostgreSQLTestRunner(verbose=verbose)

    def _log(self, message):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[Live Test] {message}")

    def _configure_django(self):
        """Configure Django with the test PostgreSQL database."""
        # Configure Django settings
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

        # Override database settings
        db_config = self.postgres_runner.get_database_config()
        os.environ.update({
            "DB_ENGINE": db_config["ENGINE"],
            "DB_NAME": db_config["NAME"],
            "DB_USER": db_config["USER"],
            "DB_HOST": db_config["HOST"],
        })
        # Only set password if it exists
        if db_config["PASSWORD"]:
            os.environ["DB_PASSWORD"] = db_config["PASSWORD"]
        # Set port as string
        os.environ["DB_PORT"] = str(db_config["PORT"])

        # Set connector
        os.environ["CONNECTOR"] = f"dbbackup.db.postgresql.{self.connector_name}"

        # Configure storage for backups - use unique directory per test
        backup_dir = os.path.join(str(self.postgres_runner.temp_dir), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        os.environ["STORAGE"] = "django.core.files.storage.FileSystemStorage"
        os.environ["STORAGE_LOCATION"] = backup_dir
        os.environ["STORAGE_OPTIONS"] = f"location={backup_dir}"

        # Setup Django only if not already configured
        if not django.apps.apps.ready:
            django.setup()

    def _create_test_data(self):
        """Create test data in the database."""
        self._log("Creating test data...")

        # Run migrations
        execute_from_command_line(["", "migrate", "--noinput"])

        # Create test models
        from tests.testapp.models import CharModel, TextModel

        # Create some test data (CharModel has max_length=10)
        char_obj = CharModel.objects.create(field="test_char")  # 9 chars, fits in 10
        text_obj = TextModel.objects.create(field="test text content for backup")

        self._log(f"Created CharModel: {char_obj}")
        self._log(f"Created TextModel: {text_obj}")

        return char_obj, text_obj

    def _verify_test_data(self, expected_char_obj, expected_text_obj):
        """Verify that test data exists and matches expectations."""
        from tests.testapp.models import CharModel, TextModel

        char_objs = CharModel.objects.all()
        text_objs = TextModel.objects.all()

        self._log(f"Found {char_objs.count()} CharModel objects")
        self._log(f"Found {text_objs.count()} TextModel objects")

        if char_objs.count() != 1 or text_objs.count() != 1:
            raise AssertionError(
                f"Expected 1 of each model, found {char_objs.count()} CharModel and {text_objs.count()} TextModel"
            )

        char_obj = char_objs.first()
        text_obj = text_objs.first()

        if char_obj.field != expected_char_obj.field:
            raise AssertionError(
                f"CharModel field mismatch: expected '{expected_char_obj.field}', got '{char_obj.field}'"
            )

        if text_obj.field != expected_text_obj.field:
            raise AssertionError(
                f"TextModel field mismatch: expected '{expected_text_obj.field}', got '{text_obj.field}'"
            )

        self._log("Test data verification passed")

    def run_backup_restore_test(self):
        """Run a complete backup and restore test cycle."""
        self._log(f"Starting backup/restore test with {self.connector_name}")

        try:
            # Setup PostgreSQL
            self.postgres_runner.setup_postgres()

            # Configure Django
            self._configure_django()

            # Create test data
            char_obj, text_obj = self._create_test_data()

            # Run backup
            self._log("Running database backup...")
            execute_from_command_line(["", "dbbackup", "--noinput"])

            # Clear test data
            self._log("Clearing test data...")
            from tests.testapp.models import CharModel, TextModel

            CharModel.objects.all().delete()
            TextModel.objects.all().delete()

            # Verify data is cleared
            if CharModel.objects.exists() or TextModel.objects.exists():
                raise AssertionError("Test data was not properly cleared")
            self._log("Test data cleared successfully")

            # Run restore
            self._log("Running database restore...")
            execute_from_command_line(["", "dbrestore", "--noinput"])

            # Verify restored data
            self._verify_test_data(char_obj, text_obj)

            self._log(f"✅ {self.connector_name} backup/restore test PASSED")
            return True

        except Exception as e:
            self._log(f"❌ {self.connector_name} backup/restore test FAILED: {e}")
            return False

        finally:
            self.postgres_runner.cleanup()


def run_single_connector_test(connector_name, verbose=False):
    """Run a test for a single connector in isolation."""

    def test_process():
        test_runner = PostgreSQLLiveTest(connector_name, verbose)
        success = test_runner.run_backup_restore_test()
        if not success:
            sys.exit(1)

    process = Process(target=test_process)
    process.start()
    process.join()

    return process.exitcode == 0


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(description="Run live PostgreSQL tests for django-dbbackup")
    parser.add_argument(
        "--connector",
        default="PgDumpConnector",
        choices=["PgDumpConnector", "PgDumpBinaryConnector", "PgDumpGisConnector"],
        help="PostgreSQL connector to test",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--all", action="store_true", help="Test all PostgreSQL connectors")

    args = parser.parse_args()

    connectors_to_test = (
        ["PgDumpConnector", "PgDumpBinaryConnector", "PgDumpGisConnector"] if args.all else [args.connector]
    )

    print("🐘 Starting PostgreSQL Live Tests for django-dbbackup (Isolated)")
    print("=" * 60)

    results = {}
    for connector in connectors_to_test:
        print(f"\nTesting {connector}...")
        results[connector] = run_single_connector_test(connector, verbose=args.verbose)

    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    for connector, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {connector}: {status}")

    total_tests = len(results)
    passed_tests = sum(results.values())
    print(f"\nResults: {passed_tests}/{total_tests} tests passed")

    # Exit with error code if any tests failed
    sys.exit(0 if passed_tests == total_tests else 1)


if __name__ == "__main__":
    main()
