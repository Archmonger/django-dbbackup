"""PostgreSQL Live Functional Test Script for django-dbbackup

Usage:
    python scripts/postgres_live_test.py [--verbose]
    python scripts/postgres_live_test.py --connector PgDumpBinaryConnector
    python scripts/postgres_live_test.py --all

It provides end-to-end validation of PostgreSQL backup/restore functionality using the
available connectors and mirrors the visual layout & summary style of the SQLite live test
(`sqlite_live_test.py`) for consistency.

Exit code 0 on success (all tested connectors passed), 1 on failure.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
from multiprocessing import Process
from pathlib import Path

from scripts._utils import get_symbols

_SYMS = get_symbols()
SYMBOL_PASS = _SYMS["PASS"]
SYMBOL_FAIL = _SYMS["FAIL"]
SYMBOL_SUMMARY = _SYMS["SUMMARY"]
SYMBOL_PG = _SYMS["PG"]
SYMBOL_TEST = _SYMS["TEST"]

# Available PostgreSQL connectors
POSTGRES_CONNECTORS = [
    "PgDumpConnector",
    "PgDumpBinaryConnector",
    "PgDumpGisConnector",
]

# Add parent directory to path to import Django modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import django
from django.core.management import execute_from_command_line

GITHUB_ACTIONS: bool = os.getenv("GITHUB_ACTIONS", "false").lower() in ("true", "1", "yes")


class PostgreSQLTestRunner:
    """Manages a test database on the existing PostgreSQL instance."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.port = 5432  # Use default PostgreSQL port
        self.temp_dir = None
        self.test_db_name = f"dbbackup_test_{int(time.time())}"  # Unique DB name
        self.superuser = "postgres"
        self.user = f"postgres_{int(time.time())}"
        self.password = "postgres"  # Password (shared by user and superuser for simplicity)
        self.db_created = False

    def _log(self, message):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[PostgreSQL Test] {message}")

    def _run_command(self, cmd, check=True, use_sudo=None, **kwargs):
        """Run a command and optionally check for errors."""
        # In GitHub Actions, don't use sudo and connect via TCP
        if GITHUB_ACTIONS:
            use_sudo = False
            # Set PostgreSQL connection environment for action-setup-postgres
            env = kwargs.get("env", os.environ.copy())
            env.update({"PGHOST": "localhost", "PGPORT": "5432", "PGUSER": "postgres", "PGPASSWORD": "postgres"})
            kwargs["env"] = env
        else:
            # For local development, use sudo if not explicitly disabled
            if use_sudo is None:
                use_sudo = os.name == "posix"

        if use_sudo:
            if isinstance(cmd, list):
                cmd = ["sudo", "-u", self.superuser] + cmd
            else:
                cmd = f"sudo -u {self.superuser} {cmd}"

        self._log(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        result = subprocess.run(cmd, shell=isinstance(cmd, str), **kwargs)
        if check and result.returncode != 0:
            # Collect stdout and stderr for better error reporting
            stdout = getattr(result, "stdout", b"")
            stderr = getattr(result, "stderr", b"")
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            error_msg = f"Command failed with exit code {result.returncode}: {cmd}"
            if stdout:
                error_msg += f"\nSTDOUT: {stdout}"
            if stderr:
                error_msg += f"\nSTDERR: {stderr}"
            raise RuntimeError(error_msg)
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

        # In CI environments, use the action-setup-postgres configured postgres user
        if GITHUB_ACTIONS:
            self._log("GitHub Actions detected, using postgres superuser as database owner")

            # action-setup-postgres already configures postgres user with password 'postgres'
            # Just create the database directly
            create_db_sql = f"CREATE DATABASE {self.test_db_name};"
            self._run_command(["psql", "-c", create_db_sql], capture_output=True)

            # Use the pre-configured postgres user credentials
            self.user = self.superuser
            self.password = "postgres"  # action-setup-postgres default
        else:
            # For local development, create a dedicated test user
            create_user_sql = (
                f"DO $$ BEGIN "
                f"IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{self.user}') THEN "
                f"CREATE USER {self.user} WITH PASSWORD '{self.password}' CREATEDB; "
                f"END IF; "
                f"END $$;"
            )

            # Create the user - capture output for better error reporting
            try:
                self._run_command(["psql", "-c", create_user_sql], capture_output=True, use_sudo=True)
            except RuntimeError as e:
                # If user creation fails, provide more context
                self._log(f"User creation failed, but attempting to continue: {e}")
                # Check if user already exists
                check_user_sql = f"SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = '{self.user}';"
                try:
                    result = self._run_command(
                        ["psql", "-t", "-c", check_user_sql], capture_output=True, check=False, use_sudo=True
                    )
                    if result.stdout and result.stdout.decode().strip():
                        self._log(f"User {self.user} already exists, continuing...")
                    else:
                        # User doesn't exist and creation failed, this is a real error
                        raise RuntimeError(f"Failed to create user {self.user} and user does not exist: {e}") from e
                except Exception as check_error:
                    self._log(f"Failed to check if user exists: {check_error}")
                    raise RuntimeError(f"User creation and verification both failed: {e}") from e

            # Create database owned by the test user
            create_db_sql = f"CREATE DATABASE {self.test_db_name} OWNER {self.user};"
            self._run_command(["psql", "-c", create_db_sql], capture_output=True, use_sudo=True)

        self.db_created = True

    def get_database_config(self):
        """Get Django database configuration for the test PostgreSQL instance."""
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": self.test_db_name,
            "USER": self.user,
            "PASSWORD": self.password,
            "HOST": "localhost",
            "PORT": self.port,
        }

    def cleanup(self):
        """Clean up the test database."""
        self._log("Cleaning up test database...")

        if self.db_created:
            try:
                # Drop the test database using psql
                drop_db_sql = f"DROP DATABASE IF EXISTS {self.test_db_name};"
                self._run_command(
                    ["psql", "-c", drop_db_sql], capture_output=True, check=False
                )  # Don't fail if database doesn't exist

                # Only drop the test user if we created one (not in CI where we use postgres superuser)
                if not GITHUB_ACTIONS and self.user != self.superuser:
                    drop_user_sql = f"DROP USER IF EXISTS {self.user};"
                    self._run_command(["psql", "-c", drop_user_sql], capture_output=True, check=False)
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

    def _test_identity_columns(self):
        """Test PostgreSQL identity column backup/restore (PostgreSQL 10+).
        
        This test validates the fix for issue #510 where identity columns
        caused restore failures without the --if-exists flag. The fix
        automatically enables --if-exists when drop=True to prevent:
        
        "ERROR: column "id" of relation ... is an identity column
         HINT: Use ALTER TABLE ... ALTER COLUMN ... DROP IDENTITY instead."
        """
        from django.db import connection
        
        # Check PostgreSQL version - identity columns require 10+
        with connection.cursor() as cursor:
            cursor.execute("SHOW server_version_num;")
            version_num = int(cursor.fetchone()[0])
            
        if version_num < 100000:  # PostgreSQL 10.0
            self._log("Skipping identity column test - requires PostgreSQL 10+")
            return True
            
        self._log(f"Testing identity column backup/restore on PostgreSQL {version_num // 10000}.{(version_num // 100) % 100}...")
        
        # Create a table with an identity column using raw SQL
        # This simulates the scenario that was failing before the fix
        table_name = "test_identity_restore_510"
        with connection.cursor() as cursor:
            # Drop table if it exists (cleanup from previous runs)
            cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
            
            # Create table with GENERATED ALWAYS AS IDENTITY column
            # This is the exact type of table that caused the issue
            cursor.execute(f"""
                CREATE TABLE {table_name} (
                    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Insert test data - PostgreSQL will auto-generate id values
            cursor.execute(f"INSERT INTO {table_name} (name) VALUES ('test_row_1'), ('test_row_2'), ('test_row_3');")
            
            # Verify data was inserted with proper identity values
            cursor.execute(f"SELECT id, name FROM {table_name} ORDER BY id;")
            original_data = cursor.fetchall()
            
        if not original_data or len(original_data) != 3:
            raise AssertionError(f"Failed to create test data with identity columns: {original_data}")
            
        self._log(f"Created identity table '{table_name}' with {len(original_data)} rows: {original_data}")
        
        # Run backup - this should work fine with any connector
        self._log("Running identity column backup...")
        from django.core.management import execute_from_command_line
        execute_from_command_line(["", "dbbackup", "--noinput"])
        
        # Clear the table data to test restore
        with connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM {table_name};")
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            if count != 0:
                raise AssertionError("Failed to clear identity table data")
                
        self._log("Cleared identity table data")
        
        # Run restore - this should succeed with the fix (auto --if-exists with drop=True)
        # Before the fix, this would fail with identity column errors when using drop=True
        # The fix ensures --if-exists is automatically added when drop=True
        self._log("Running identity column restore (testing issue #510 fix)...")
        execute_from_command_line(["", "dbrestore", "--noinput"])
        
        # Verify the data was restored correctly
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT id, name FROM {table_name} ORDER BY id;")
            restored_data = cursor.fetchall()
            
        if restored_data != original_data:
            raise AssertionError(
                f"Identity column data mismatch after restore:\nOriginal: {original_data}\nRestored: {restored_data}"
            )
            
        self._log(f"✅ Successfully restored {len(restored_data)} rows with identity columns")
        
        # Clean up - drop the test table
        with connection.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
            
        self._log("Identity column test completed successfully")
        return True

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

            # Run identity column test for PgDumpBinaryConnector (where the fix was applied)
            if self.connector_name == "PgDumpBinaryConnector":
                self._log("Running additional identity column test for PgDumpBinaryConnector...")
                try:
                    self._test_identity_columns()
                    self._log(f"{SYMBOL_PASS} Identity column test PASSED")
                except Exception as e:
                    self._log(f"{SYMBOL_FAIL} Identity column test FAILED: {e}")
                    return False

            self._log(f"{SYMBOL_PASS} {self.connector_name} backup/restore test PASSED")
            return True

        except Exception as e:
            self._log(f"{SYMBOL_FAIL} {self.connector_name} backup/restore test FAILED: {e}")
            return False

        finally:
            self.postgres_runner.cleanup()


def _connector_test_entry(connector_name: str, verbose: bool):  # pragma: no cover - executed in subprocess
    """Subprocess entry point to run a single connector test.

    Needs to be at module top-level so it can be imported/pickled on Windows
    (the 'spawn' start method). Exits with status code 1 if the test fails.
    """
    test_runner = PostgreSQLLiveTest(connector_name, verbose)
    success = test_runner.run_backup_restore_test()
    if not success:
        sys.exit(1)


def run_single_connector_test(connector_name, verbose=False):
    """Run a test for a single connector in isolation using a subprocess.

    On Windows, multiprocessing with nested (local) functions fails because they
    are not picklable under the 'spawn' start method. We therefore provide a
    top-level function as the process target. If an unexpected multiprocessing
    failure occurs on Windows (e.g., permissions), we gracefully fall back to
    in-process execution to avoid masking all connector results.
    """

    # Normal path: run in a separate process for isolation
    def _run_subprocess():  # local helper kept simple; not used as target
        process_local = Process(target=_connector_test_entry, args=(connector_name, verbose))
        process_local.start()
        process_local.join()
        return process_local

    try:
        process = _run_subprocess()
        if process.exitcode is None:
            return False
        if process.exitcode != 0 and os.name == "nt":  # Fallback path on Windows
            # Retry in-process so at least we capture a meaningful failure message
            test_runner = PostgreSQLLiveTest(connector_name, verbose)
            return test_runner.run_backup_restore_test()
        return process.exitcode == 0
    except AttributeError as exc:  # Defensive: pickling or spawn related
        if os.name == "nt":
            print(f"{SYMBOL_FAIL} Multiprocessing issue on Windows ({exc}); running in-process instead.")
            test_runner = PostgreSQLLiveTest(connector_name, verbose)
            return test_runner.run_backup_restore_test()
        raise


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(description="Run live PostgreSQL tests for django-dbbackup")
    parser.add_argument(
        "--connector",
        default="PgDumpConnector",
        choices=POSTGRES_CONNECTORS,
        help="PostgreSQL connector to test (default: %(default)s)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--all", action="store_true", help="Test all PostgreSQL connectors")

    args = parser.parse_args()

    connectors_to_test = POSTGRES_CONNECTORS if args.all else [args.connector]

    print(f"{SYMBOL_PG} Starting PostgreSQL Live Tests for django-dbbackup (Isolated)")

    results = {}
    for connector in connectors_to_test:
        print(f"\n{SYMBOL_TEST} Testing {connector}...")
        results[connector] = run_single_connector_test(connector, verbose=args.verbose)
        passed = results[connector]
        status = f"{SYMBOL_PASS} PASSED" if passed else f"{SYMBOL_FAIL} FAILED"
        print(f"  {connector}: {status}")

    # Summary
    print(f"\n{SYMBOL_SUMMARY} PostgreSQL Connector Test Summary")
    overall_success = True
    for connector, passed in results.items():
        overall_success &= passed
        symbol = SYMBOL_PASS if passed else SYMBOL_FAIL
        print(f"  {symbol} {connector}")

    # Exit with error code if any tests failed
    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    main()
