# ruff: noqa: TRY300, BLE001
"""SQLite Live Functional Test Script for django-dbbackup

Usage:
    python scripts/sqlite_live_test.py [--verbose]
    python scripts/sqlite_live_test.py --connector SqliteConnector
    python scripts/sqlite_live_test.py --all [--verbose]

It relies on environment variables already defined by the functional Hatch
environment (see `[tool.hatch.envs.functional.env-vars]` in `pyproject.toml`).

Exit code 0 on success, 1 on failure.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import shutil
import subprocess
import sys
import traceback

from scripts._utils import get_symbols

_SYMS = get_symbols()
SYMBOL_PASS = _SYMS["PASS"]
SYMBOL_FAIL = _SYMS["FAIL"]
SYMBOL_SUMMARY = _SYMS["SUMMARY"]
SYMBOL_TEST = _SYMS["TEST"]


def log(msg: str, *, verbose: bool) -> None:
    if verbose:
        print(f"[SQLite Test] {msg}")


def configure_django(verbose: bool) -> None:
    # Ensure DJANGO_SETTINGS_MODULE is set; functional env already does this
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")
    import django  # (import after setting env var)
    from django.apps import apps

    if not apps.ready:
        log("Initializing Django...", verbose=verbose)
        django.setup()


def run_management_command(cmd: list[str], *, verbose: bool) -> None:
    from django.core.management import execute_from_command_line

    log("Running: " + " ".join(cmd[1:]), verbose=verbose)
    execute_from_command_line(cmd)


def remove_if_exists(path: str, *, verbose: bool) -> None:
    if os.path.exists(path):
        log(f"Removing {path}", verbose=verbose)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)


SQLITE_CONNECTORS = [
    "SqliteConnector",
    "SqliteBackupConnector",
    "SqliteCPConnector",
]


def _run_all(connectors, verbose: bool) -> int:
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
    print(f"\n{SYMBOL_SUMMARY} SQLite Connector Test Summary")
    for name, passed in results.items():
        status = SYMBOL_PASS if passed else SYMBOL_FAIL
        print(f"  {status} {name}")
    return 0 if overall_success else 1


def main() -> int:  # (complexity acceptable for test harness)
    parser = argparse.ArgumentParser(description="Run live SQLite functional tests for django-dbbackup")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--connector",
        choices=SQLITE_CONNECTORS,
        default="SqliteConnector",
        help="SQLite connector to test (default: %(default)s)",
    )
    parser.add_argument("--all", action="store_true", help="Test all SQLite connectors")
    args = parser.parse_args()
    verbose = args.verbose

    if args.all:
        return _run_all(SQLITE_CONNECTORS, verbose)

    # Ensure connector environment variable is set before Django loads
    os.environ["CONNECTOR"] = f"dbbackup.db.sqlite.{args.connector}"

    # Paths derived from environment or defaults matching functional env
    db_path = os.environ.get("DB_NAME", "tmp/test_db.sqlite3")
    backups_dir = os.environ.get("STORAGE_LOCATION", "tmp/backups/")
    media_root = os.environ.get("MEDIA_ROOT", "tmp/media/")

    try:
        # 1. Prepare directories
        os.makedirs(backups_dir, exist_ok=True)
        os.makedirs(media_root, exist_ok=True)
        log(f"Using connector: {args.connector}", verbose=verbose)
        log(f"Using database file: {db_path}", verbose=verbose)
        log(f"Backups directory: {backups_dir}", verbose=verbose)
        log(f"Media root: {media_root}", verbose=verbose)

        # 2. Remove existing DB
        remove_if_exists(db_path, verbose=verbose)

        # 3. Configure Django & migrate
        configure_django(verbose)
        run_management_command(["", "migrate", "--noinput"], verbose=verbose)

        # 4. Create test model instances (expanded vs legacy 'feed')
        from tests.testapp.models import CharModel, TextModel

        CharModel.objects.bulk_create([
            CharModel(field="test1"),
            CharModel(field="test2"),
        ])
        complex_text = "Line1;\nLine2; with semicolons ; end"
        TextModel.objects.create(field=complex_text)
        char_count_before = CharModel.objects.count()
        text_count_before = TextModel.objects.count()
        assert char_count_before == 2, "Incorrect initial CharModel count"
        assert text_count_before == 1, "Incorrect initial TextModel count"
        log(
            f"Created test data: {char_count_before} CharModel, {text_count_before} TextModel (complex content length={len(complex_text)})",
            verbose=verbose,
        )

        # 5. Database backup (capture newest filename afterwards)
        pre_existing = set(os.listdir(backups_dir))
        run_management_command(["", "dbbackup", "--noinput"], verbose=verbose)
        post_existing = set(os.listdir(backups_dir))
        new_files = sorted(post_existing - pre_existing)
        latest_backup = new_files[-1] if new_files else None
        log(f"Database backup completed (file: {latest_backup})", verbose=verbose)

        # 6. Delete data
        CharModel.objects.all().delete()
        TextModel.objects.all().delete()
        assert CharModel.objects.count() == 0
        assert TextModel.objects.count() == 0
        log("Deleted CharModel and TextModel objects", verbose=verbose)

        # 7. Database restore (force correct backup when extension differs)
        restore_cmd = ["", "dbrestore", "--noinput"]
        if latest_backup:
            restore_cmd.extend(["-i", latest_backup])
        run_management_command(restore_cmd, verbose=verbose)

        # 8. Assert data restored
        restored_char_count = CharModel.objects.count()
        restored_text_count = TextModel.objects.count()
        assert (
            restored_char_count == char_count_before
        ), f"CharModel count mismatch: expected {char_count_before}, got {restored_char_count}"
        assert (
            restored_text_count == text_count_before
        ), f"TextModel count mismatch: expected {text_count_before}, got {restored_text_count}"
        # Validate complex content integrity
        first_text = TextModel.objects.first()
        restored_text = first_text.field if first_text else None
        assert restored_text == complex_text, "TextModel content mismatch after restore"
        log(
            "Database test passed (counts and content integrity verified)",
            verbose=verbose,
        )

        # 9. Create multiple media files and dirs (mirrors legacy functional.sh scenarios)
        media_specs = {
            "foo": "foo",  # simple file
            os.path.join("bar", "ham"): "ham",  # nested file
            "test.txt": "test content",  # original single file
        }
        for rel_path, content in media_specs.items():
            target = os.path.join(media_root, rel_path)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(content)
        for rel_path in media_specs:
            assert os.path.exists(os.path.join(media_root, rel_path)), f"Missing media test file {rel_path}"
        log(f"Created media test files: {', '.join(media_specs.keys())}", verbose=verbose)

        # 10. Media backup
        run_management_command(["", "mediabackup", "--noinput"], verbose=verbose)
        log("Media backup completed", verbose=verbose)

        # 11. Delete media file & restore
        for rel_path in media_specs:
            target = os.path.join(media_root, rel_path)
            if os.path.exists(target):
                os.remove(target)
        # Remove created directories (best effort)
        with contextlib.suppress(Exception):
            shutil.rmtree(os.path.join(media_root, "bar"))
        for rel_path in media_specs:
            assert not os.path.exists(os.path.join(media_root, rel_path)), "Failed to delete media files before restore"
        run_management_command(["", "mediarestore", "--noinput"], verbose=verbose)

        # 12. Assert media restored
        for rel_path, content in media_specs.items():
            target = os.path.join(media_root, rel_path)
            assert os.path.exists(target), f"Media restore missing file {rel_path}"
            with open(target, encoding="utf-8") as fh:
                restored_content = fh.read()
            assert restored_content == content, f"Content mismatch for {rel_path}"
        log("Media test passed (multi-file + content integrity)", verbose=verbose)

        return 0
    except Exception as exc:
        print(f"{SYMBOL_FAIL} SQLite functional test FAILED:", exc, file=sys.stderr)
        traceback.print_exc()
        return 1
    finally:
        # Clean up database file (mirrors previous inline step) but leave backups for inspection
        with contextlib.suppress(Exception):
            remove_if_exists(db_path, verbose=verbose)


if __name__ == "__main__":  # pragma: no cover - executed as script
    sys.exit(main())
