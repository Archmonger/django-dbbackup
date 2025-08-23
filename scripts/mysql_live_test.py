"""MySQL Live Functional Test Script for django-dbbackup

Usage:
    python scripts/mysql_live_test.py [--verbose]
    python scripts/mysql_live_test.py --connector MysqlDumpConnector
    python scripts/mysql_live_test.py --all

It provides end-to-end validation of MySQL backup/restore functionality using the
available connectors and mirrors the visual layout & summary style of the SQLite and
PostgreSQL live tests for consistency.

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
SYMBOL_MYSQL = _SYMS["MYSQL"]
SYMBOL_TEST = _SYMS["TEST"]
SYMBOL_SKIP = _SYMS["SKIP"]
SYMBOL_INFO = _SYMS["INFO"]

# Available MySQL connectors
MYSQL_CONNECTORS = [
    "MysqlDumpConnector",
]

# Add parent directory to path to import Django modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import django
from django.core.management import execute_from_command_line

GITHUB_ACTIONS: bool = os.getenv("GITHUB_ACTIONS", "false").lower() in ("true", "1", "yes")


class MySQLTestRunner:
    """Manages a test database on the existing MySQL instance."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.temp_dir = None
        self.test_db_name = f"dbbackup_test_{int(time.time())}"
        # Allow environment overrides so CI or developers can point at
        # an existing server without editing the script. These defaults
        # mirror the prior hard‑coded values but now support more setups
        # (e.g. root account with socket auth, custom host, empty password).
        self.user = os.getenv("MYSQL_TEST_USER", "dbbackup_test_user")
        # Password used for the dedicated test user we create
        self.password = os.getenv("MYSQL_TEST_PASSWORD", "mysql")
        # Force TCP by default (127.0.0.1) to avoid relying on a Unix domain
        # socket path that varies across distros (/var/run vs /run) and to
        # work with Docker/remote services. A user can still supply the
        # classic 'localhost' or a remote hostname via env var.
        self.host = os.getenv("MYSQL_HOST", "localhost")
        self.port = int(os.getenv("MYSQL_PORT", "3306"))
        # Superuser used to bootstrap the test DB & user. Allow empty password
        # (common with auth_socket); we'll attempt multiple auth modes.
        self.superuser = os.getenv("MYSQL_SUPERUSER", "root")
        self.superpassword = os.getenv("MYSQL_SUPERPASSWORD", os.getenv("MYSQL_ROOT_PASSWORD", "mysql"))
        self.db_created = False
        self.user_created = False

    def _log(self, message):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[MySQL Test] {message}")

    def _run_command(self, cmd, check=True, capture_output=False, **kwargs):
        """Run a command and optionally check for errors."""
        self._log(f"Running: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=capture_output, text=True, **kwargs)
        if check and result.returncode != 0:
            error_msg = f"Command failed with exit code {result.returncode}: {' '.join(cmd)}"
            if capture_output:
                if result.stdout:
                    error_msg += f"\nSTDOUT: {result.stdout}"
                if result.stderr:
                    error_msg += f"\nSTDERR: {result.stderr}"
            raise RuntimeError(error_msg)
        return result

    def setup_mysql(self):
        """Set up a test database on the existing MySQL instance."""

        if not shutil.which("mysql") or not shutil.which("mysqldump"):
            install_instructions = ""
            if os.name == "posix":
                install_instructions = (
                    "\nInstall by running 'sudo apt install mysql-client mysql-server'\n"
                    "... then run 'sudo service mysql start' to start the server."
                )
            elif os.name == "nt":
                install_instructions = (
                    "\nInstall MySQL from https://dev.mysql.com/downloads/installer/ "
                    "and ensure mysql and mysqldump are in your PATH."
                )
            raise RuntimeError(f"MySQL client tools (mysql, mysqldump, etc) are not installed!{install_instructions}")

        self._log("Setting up test database...")
        self.temp_dir = tempfile.mkdtemp(prefix="dbbackup_mysql_")
        try:
            # Create test database
            self._create_test_database()

        except Exception as e:
            self.cleanup()
            raise RuntimeError(f"Failed to set up MySQL: {e}") from e

    def _create_test_database(self):
        """Create the test database."""
        self._log(f"Creating test database: {self.test_db_name}")

        # Build two candidate admin commands: with password (if provided) & without.
        base_common = ["-h", self.host, "-P", str(self.port), "--protocol=TCP"]
        candidate_cmds = []
        if self.superpassword:
            candidate_cmds.append(["mysql", "-u", self.superuser, f"--password={self.superpassword}"] + base_common)
        candidate_cmds.append(["mysql", "-u", self.superuser] + base_common)

        last_err = None
        for cmd_parts in candidate_cmds:
            try:
                self._log(
                    "Trying MySQL connection with: "
                    + " ".join([c for c in cmd_parts if not c.startswith("--password=")])
                )
                # Smoke test
                self._run_command(cmd_parts + ["-e", "SELECT 1;"], capture_output=True)
                # Create database
                self._run_command(
                    cmd_parts + ["-e", f"CREATE DATABASE IF NOT EXISTS {self.test_db_name};"], capture_output=True
                )
                # Create user (both '%' and 'localhost' host patterns)
                pw_clause = f" IDENTIFIED BY '{self.password}'" if self.password else ""
                create_user_sql = (
                    f"CREATE USER IF NOT EXISTS '{self.user}'@'%' {pw_clause};"
                    f"CREATE USER IF NOT EXISTS '{self.user}'@'localhost' {pw_clause};"
                    f"GRANT ALL PRIVILEGES ON {self.test_db_name}.* TO '{self.user}'@'%';"
                    f"GRANT ALL PRIVILEGES ON {self.test_db_name}.* TO '{self.user}'@'localhost';"
                    "FLUSH PRIVILEGES;"
                )
                self._run_command(cmd_parts + ["-e", create_user_sql], capture_output=True, check=False)
                self.user_created = True
                self.mysql_base_cmd = cmd_parts  # keep for cleanup
                self.db_created = True
                self._log("Successfully connected to MySQL and created database & user over TCP")
                return
            except RuntimeError as exc:
                last_err = exc
                self._log(f"Attempt failed: {exc}")

        raise RuntimeError(
            "Could not connect to MySQL with any authentication method. Ensure the server is running "
            "and environment vars MYSQL_HOST / MYSQL_PORT / MYSQL_SUPERUSER / MYSQL_SUPERPASSWORD are correct."
        ) from last_err

    def get_database_config(self):
        """Get Django database configuration for the test MySQL instance."""
        return {
            "ENGINE": "django.db.backends.mysql",
            "NAME": self.test_db_name,
            "USER": self.user,
            "PASSWORD": self.password,
            # Use provided host explicitly (avoid default socket resolution)
            "HOST": self.host,
            "PORT": self.port,
            "OPTIONS": {
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }

    def cleanup(self):
        """Clean up the test database."""
        self._log("Cleaning up test database...")

        if self.db_created and hasattr(self, "mysql_base_cmd"):
            try:
                self._log(f"Dropping test database: {self.test_db_name}")
                cmd = self.mysql_base_cmd + ["-e", f"DROP DATABASE IF EXISTS {self.test_db_name};"]
                self._run_command(cmd, check=False)
            except Exception as e:
                self._log(f"Warning: Failed to drop test database: {e}")

        if self.user_created and hasattr(self, "mysql_base_cmd") and not GITHUB_ACTIONS:
            try:
                self._log(f"Dropping test user: {self.user}")
                # Drop both '%' and 'localhost' host specs just in case
                drop_stmt = (
                    f"DROP USER IF EXISTS '{self.user}'@'%';"
                    f"DROP USER IF EXISTS '{self.user}'@'localhost';"
                    "FLUSH PRIVILEGES;"
                )
                cmd = self.mysql_base_cmd + ["-e", drop_stmt]
                self._run_command(cmd, check=False)
            except Exception as e:
                self._log(f"Warning: Failed to drop test user: {e}")

        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


class MySQLLiveTest:
    """Runs live tests against MySQL connectors."""

    def __init__(self, connector_name="MysqlDumpConnector", verbose=False):
        self.connector_name = connector_name
        self.verbose = verbose
        self.mysql_runner = MySQLTestRunner(verbose=verbose)

    def _log(self, message):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[Live Test] {message}")

    def _configure_django(self):
        """Configure Django with the test MySQL database."""
        # Configure Django settings
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

        # Override database settings
        db_config = self.mysql_runner.get_database_config()
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
        os.environ["CONNECTOR"] = f"dbbackup.db.mysql.{self.connector_name}"

        # Configure storage for backups - use unique directory per test
        backup_dir = os.path.join(str(self.mysql_runner.temp_dir), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        os.environ.update({
            "STORAGE": "django.core.files.storage.FileSystemStorage",
            "STORAGE_LOCATION": backup_dir,
            "STORAGE_OPTIONS": f"location={backup_dir}",
            "MEDIA_ROOT": os.path.join(str(self.mysql_runner.temp_dir), "media"),
        })

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
            # Setup MySQL
            self.mysql_runner.setup_mysql()

            # Configure Django
            self._configure_django()

            # Create test data
            char_obj, text_obj = self._create_test_data()

            # Run backup
            self._log("Running database backup...")
            execute_from_command_line(["", "dbbackup", "--noinput"])

            # Create media files and backup
            media_dir = os.environ["MEDIA_ROOT"]
            os.makedirs(media_dir, exist_ok=True)

            # Create test media files
            test_file = os.path.join(media_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            self._log("Running media backup...")
            execute_from_command_line(["", "mediabackup", "--noinput"])

            # Clear test data
            self._log("Clearing test data...")
            from tests.testapp.models import CharModel, TextModel

            CharModel.objects.all().delete()
            TextModel.objects.all().delete()

            # Remove media files
            if os.path.exists(test_file):
                os.remove(test_file)

            # Verify data is cleared
            if CharModel.objects.exists() or TextModel.objects.exists():
                raise AssertionError("Test data was not properly cleared")
            if os.path.exists(test_file):
                raise AssertionError("Media files were not properly cleared")
            self._log("Test data cleared successfully")

            # Run restore
            self._log("Running database restore...")
            execute_from_command_line(["", "dbrestore", "--noinput"])

            self._log("Running media restore...")
            execute_from_command_line(["", "mediarestore", "--noinput"])

            # Verify restored data
            self._verify_test_data(char_obj, text_obj)

            # Verify restored media
            if not os.path.exists(test_file):
                raise AssertionError(f"Media file not restored: {test_file}")

            with open(test_file, "r") as f:
                content = f.read()
                if content != "test content":
                    raise AssertionError(f"Media file content mismatch: expected 'test content', got '{content}'")

            self._log(f"{SYMBOL_PASS} {self.connector_name} backup/restore test PASSED")
            return True

        except RuntimeError as e:
            if "Could not connect to MySQL" in str(e) or "MySQL client tools" in str(e):
                self._log(f"MySQL not available, skipping test: {e}")
                return False if GITHUB_ACTIONS else "skipped"
            else:
                self._log(f"{SYMBOL_FAIL} {self.connector_name} backup/restore test FAILED: {e}")
                return False
        except Exception as e:
            self._log(f"{SYMBOL_FAIL} {self.connector_name} backup/restore test FAILED: {e}")
            return False

        finally:
            self.mysql_runner.cleanup()


def _connector_test_entry(connector_name: str, verbose: bool):  # pragma: no cover - executed in subprocess
    """Subprocess entry point to run a single connector test.

    Needs to be at module top-level so it can be imported/pickled on Windows
    (the 'spawn' start method). Exits with status code 1 if the test fails,
    2 if the test is skipped.
    """
    test_runner = MySQLLiveTest(connector_name, verbose)
    result = test_runner.run_backup_restore_test()
    if result == "skipped":
        sys.exit(2)  # Special exit code for skipped
    elif not result:
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
        if process.exitcode == 2:
            return "skipped"
        if process.exitcode != 0 and os.name == "nt":  # Fallback path on Windows
            # Retry in-process so at least we capture a meaningful failure message
            test_runner = MySQLLiveTest(connector_name, verbose)
            return test_runner.run_backup_restore_test()
        return process.exitcode == 0
    except AttributeError as exc:  # Defensive: pickling or spawn related
        if os.name == "nt":
            print(f"{SYMBOL_FAIL} Multiprocessing issue on Windows ({exc}); running in-process instead.")
            test_runner = MySQLLiveTest(connector_name, verbose)
            return test_runner.run_backup_restore_test()
        raise


def _run_all(connectors, verbose: bool) -> int:
    """Run tests for all connectors."""
    overall_success = True
    results = {}
    skipped_count = 0

    for connector in connectors:
        print(f"\n{SYMBOL_TEST} Testing {connector}...")
        result = run_single_connector_test(connector, verbose=verbose)

        if result == "skipped":
            passed = "skipped"
            status = f"{SYMBOL_SKIP}  SKIPPED"
            skipped_count += 1
        elif result:
            passed = True
            status = f"{SYMBOL_PASS} PASSED"
        else:
            passed = False
            status = f"{SYMBOL_FAIL} FAILED"
            overall_success = False

        results[connector] = passed
        print(f"  {connector}: {status}")

    # Summary
    print(f"\n{SYMBOL_SUMMARY} MySQL Connector Test Summary")
    for connector, passed in results.items():
        if passed == "skipped":
            status = SYMBOL_SKIP
        elif passed:
            status = SYMBOL_PASS
        else:
            status = SYMBOL_FAIL
        print(f"  {status} {connector}")

    if skipped_count == len(connectors):
        print(f"  {SYMBOL_INFO}  All tests skipped (MySQL not available)")
        return 0  # Don't fail if MySQL is not available

    return 0 if overall_success else 1


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(description="Run live MySQL tests for django-dbbackup")
    parser.add_argument(
        "--connector",
        default="MysqlDumpConnector",
        choices=MYSQL_CONNECTORS,
        help="MySQL connector to test (default: %(default)s)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--all", action="store_true", help="Test all MySQL connectors")

    args = parser.parse_args()

    print(f"{SYMBOL_MYSQL} Starting MySQL Live Tests for django-dbbackup (Isolated)")

    if args.all:
        return _run_all(MYSQL_CONNECTORS, args.verbose)

    # Run single connector test
    result = run_single_connector_test(args.connector, verbose=args.verbose)

    if result == "skipped":
        return 2  # Special exit code for skipped
    elif result:
        return 0
    else:
        return 1


if __name__ == "__main__":  # pragma: no cover - executed as script
    sys.exit(main())
