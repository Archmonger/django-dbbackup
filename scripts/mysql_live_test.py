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
from pathlib import Path

# Add parent directory to path to import Django modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts._utils import get_symbols

_SYMS = get_symbols()
SYMBOL_PASS = _SYMS["PASS"]
SYMBOL_FAIL = _SYMS["FAIL"]
SYMBOL_SUMMARY = _SYMS["SUMMARY"]
SYMBOL_MYSQL = "🐬"  # MySQL dolphin emoji
SYMBOL_TEST = _SYMS["TEST"]

# Available MySQL connectors  
MYSQL_CONNECTORS = [
    "MysqlDumpConnector",
]

import django
from django.core.management import execute_from_command_line

GITHUB_ACTIONS: bool = os.getenv("GITHUB_ACTIONS", "false").lower() in ("true", "1", "yes")


class MySQLTestRunner:
    """Manages a test database on the existing MySQL instance."""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.temp_dir = Path(tempfile.mkdtemp(prefix="mysql_live_test_"))
        self.test_db_name = f"dbbackup_test_{int(time.time())}"
        self.user = "dbbackup_test_user"
        self.password = "test_password_123"
        self.host = "localhost"
        self.port = 3306
        self.superuser = "root"
        self.db_created = False
        self.user_created = False
    
    def _log(self, message):
        if self.verbose:
            print(f"[MySQL Test] {message}")
    
    def _run_command(self, cmd, capture_output=False, use_sudo=False):
        """Run a command and return stdout."""
        if use_sudo and not GITHUB_ACTIONS:
            # For local development, might need sudo for MySQL operations
            cmd = ["sudo"] + cmd
        
        self._log(f"Running: {' '.join(cmd)}")
        
        if capture_output:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"Command failed: {result.stderr}")
            return result.stdout.strip()
        else:
            result = subprocess.run(cmd)
            if result.returncode != 0:
                raise RuntimeError(f"Command failed with exit code {result.returncode}")
    
    def _create_test_database(self):
        """Create the test database."""
        self._log(f"Creating test database: {self.test_db_name}")
        
        # Try different MySQL authentication methods
        mysql_commands = [
            ["sudo", "mysql"],  # auth_socket (common on Ubuntu)
            ["mysql", "-u", "root"],  # no password
            ["mysql", "-u", "root", "-p"],  # password prompt (will fail in automation)
        ]
        
        if GITHUB_ACTIONS:
            self._log("GitHub Actions detected, using root user as database owner")
            # In CI, try the standard root access
            mysql_commands = [
                ["mysql", "-u", "root"],
                ["mysql", "-u", "root", "-h", "localhost"],
            ]
            self.user = self.superuser
            self.password = ""  # No password for root in CI typically
        else:
            # For local development, use sudo mysql (auth_socket)
            self.user = self.superuser  # Use root for simplicity
            self.password = ""
        
        # Try to connect and create database
        create_db_sql = f"CREATE DATABASE IF NOT EXISTS {self.test_db_name};"
        
        for mysql_cmd in mysql_commands:
            try:
                cmd = mysql_cmd + ["-e", create_db_sql]
                self._log(f"Trying MySQL connection with: {' '.join(mysql_cmd)}")
                self._run_command(cmd, capture_output=True)
                self._log("Successfully connected to MySQL and created database")
                
                # Test the connection works
                test_cmd = mysql_cmd + ["-e", "SELECT 1;"]
                self._run_command(test_cmd, capture_output=True)
                
                # Store the working command for later use
                self.mysql_base_cmd = mysql_cmd
                self.db_created = True
                return
                
            except RuntimeError as e:
                self._log(f"MySQL connection failed with {' '.join(mysql_cmd)}: {e}")
                continue
        
        # If all methods fail, raise an error
        raise RuntimeError("Could not connect to MySQL with any authentication method. "
                         "Please ensure MySQL is running and accessible.")
    
    def get_database_config(self):
        """Return Django database configuration."""
        return {
            "ENGINE": "django.db.backends.mysql",
            "NAME": self.test_db_name,
            "USER": self.user,
            "PASSWORD": self.password,
            "HOST": self.host,
            "PORT": self.port,
            "OPTIONS": {
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    
    def cleanup(self):
        """Clean up test database and user."""
        if self.db_created and hasattr(self, 'mysql_base_cmd'):
            try:
                self._log(f"Dropping test database: {self.test_db_name}")
                cmd = self.mysql_base_cmd + ["-e", f"DROP DATABASE IF EXISTS {self.test_db_name};"]
                self._run_command(cmd)
            except Exception as e:
                self._log(f"Failed to drop database: {e}")
        
        if self.user_created and hasattr(self, 'mysql_base_cmd') and not GITHUB_ACTIONS:
            try:
                self._log(f"Dropping test user: {self.user}")
                cmd = self.mysql_base_cmd + ["-e", f"DROP USER IF EXISTS '{self.user}'@'localhost';"]
                self._run_command(cmd)
            except Exception as e:
                self._log(f"Failed to drop user: {e}")
        
        # Clean up temp directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self._log(f"Removed temp directory: {self.temp_dir}")


class MySQLLiveTest:
    """Runs live tests against MySQL connectors."""
    
    def __init__(self, connector_name, verbose=False):
        self.connector_name = connector_name
        self.verbose = verbose
        self.mysql_runner = MySQLTestRunner(verbose=verbose)
    
    def _log(self, message):
        if self.verbose:
            print(f"[MySQL Live Test] {message}")
    
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
        
        # Initialize Django
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
    
    def _verify_test_data(self, expected_char_count, expected_text_count):
        """Verify that the expected test data exists."""
        from tests.testapp.models import CharModel, TextModel
        
        actual_char_count = CharModel.objects.count()
        actual_text_count = TextModel.objects.count()
        
        self._log(f"Data verification - CharModel: {actual_char_count}/{expected_char_count}, TextModel: {actual_text_count}/{expected_text_count}")
        
        if actual_char_count != expected_char_count:
            raise AssertionError(f"CharModel count mismatch: expected {expected_char_count}, got {actual_char_count}")
        if actual_text_count != expected_text_count:
            raise AssertionError(f"TextModel count mismatch: expected {expected_text_count}, got {actual_text_count}")
        
        return True
    
    def run_test(self):
        """Run the full backup/restore test cycle."""
        try:
            self._log(f"Starting MySQL live test for {self.connector_name}")
            
            # 1. Setup MySQL database
            self.mysql_runner._create_test_database()
            
            # 2. Configure Django
            self._configure_django()
            
            # 3. Create test data
            char_obj, text_obj = self._create_test_data()
            expected_char_count = 1
            expected_text_count = 1
            
            # 4. Verify initial data
            self._verify_test_data(expected_char_count, expected_text_count)
            
            # 5. Create database backup
            self._log("Creating database backup...")
            execute_from_command_line(["", "dbbackup", "--noinput"])
            
            # 6. Create media files and backup
            media_dir = os.environ["MEDIA_ROOT"]
            os.makedirs(media_dir, exist_ok=True)
            
            # Create test media files
            test_file = os.path.join(media_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")
            
            self._log("Creating media backup...")
            execute_from_command_line(["", "mediabackup", "--noinput"])
            
            # 7. Clear the database
            self._log("Clearing database for restore test...")
            from tests.testapp.models import CharModel, TextModel
            CharModel.objects.all().delete()
            TextModel.objects.all().delete()
            
            # Remove media files
            if os.path.exists(test_file):
                os.remove(test_file)
            
            # 8. Restore database
            self._log("Restoring database backup...")
            execute_from_command_line(["", "dbrestore", "--noinput"])
            
            # 9. Restore media
            self._log("Restoring media backup...")
            execute_from_command_line(["", "mediarestore", "--noinput"])
            
            # 10. Verify restored data
            self._verify_test_data(expected_char_count, expected_text_count)
            
            # 11. Verify restored media
            if not os.path.exists(test_file):
                raise AssertionError(f"Media file not restored: {test_file}")
            
            with open(test_file, "r") as f:
                content = f.read()
                if content != "test content":
                    raise AssertionError(f"Media file content mismatch: expected 'test content', got '{content}'")
            
            self._log(f"MySQL live test for {self.connector_name} completed successfully")
            return True
            
        except Exception as e:
            self._log(f"MySQL live test for {self.connector_name} failed: {e}")
            return False
        finally:
            # Cleanup
            self.mysql_runner.cleanup()


def _run_all(connectors, verbose: bool) -> int:
    """Run tests for all connectors."""
    overall_success = True
    results = {}
    
    for name in connectors:
        cmd = [sys.executable, __file__, "--connector", name]
        if verbose:
            cmd.append("-v")
        
        print(f"\n{SYMBOL_TEST} Testing {name}...")
        proc = subprocess.run(cmd, check=False)
        passed = proc.returncode == 0
        results[name] = passed
        status = f"{SYMBOL_PASS} PASSED" if passed else f"{SYMBOL_FAIL} FAILED"
        print(f"  {name}: {status}")
        overall_success &= passed
    
    print(f"\n{SYMBOL_SUMMARY} MySQL Connector Test Summary")
    for name, passed in results.items():
        status = SYMBOL_PASS if passed else SYMBOL_FAIL
        print(f"  {status} {name}")
    
    return 0 if overall_success else 1


def main() -> int:
    """Main entry point for MySQL live tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run live MySQL functional tests for django-dbbackup")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--connector",
        choices=MYSQL_CONNECTORS,
        default="MysqlDumpConnector",
        help="MySQL connector to test (default: %(default)s)",
    )
    parser.add_argument("--all", action="store_true", help="Test all MySQL connectors")
    
    args = parser.parse_args()
    verbose = args.verbose
    
    if args.all:
        return _run_all(MYSQL_CONNECTORS, verbose)
    
    # Run single connector test
    test = MySQLLiveTest(args.connector, verbose=verbose)
    success = test.run_test()
    return 0 if success else 1


if __name__ == "__main__":  # pragma: no cover - executed as script
    sys.exit(main())