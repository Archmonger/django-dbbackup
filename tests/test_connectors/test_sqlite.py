from io import BytesIO
from unittest.mock import mock_open, patch

from django.db import connection
from django.test import TestCase

from dbbackup.db.sqlite import SqliteBackupConnector, SqliteConnector, SqliteCPConnector
from tests.testapp.models import CharModel, TextModel


class SqliteConnectorTest(TestCase):
    def test_write_dump(self):
        dump_file = BytesIO()
        connector = SqliteConnector()
        connector._write_dump(dump_file)
        dump_file.seek(0)
        for line in dump_file:
            self.assertTrue(line.strip().endswith(b";"))

    def test_create_dump(self):
        connector = SqliteConnector()
        dump = connector.create_dump()
        self.assertTrue(dump.read())

    def test_create_dump_with_unicode(self):
        CharModel.objects.create(field="\xe9")
        connector = SqliteConnector()
        dump = connector.create_dump()
        self.assertTrue(dump.read())

    def test_create_dump_with_newline(self):
        TextModel.objects.create(field=f'INSERT ({"foo" * 5000}\nbar\n WHERE \nbaz IS\n "great" );\n')

        connector = SqliteConnector()
        dump = connector.create_dump()
        self.assertTrue(dump.read())

    def test_restore_dump(self):
        TextModel.objects.create(field="T\nf\nw\nnl")
        connector = SqliteConnector()
        dump = connector.create_dump()
        connector.restore_dump(dump)

    def test_restore_dump_with_multiline_js_content(self):
        """Test restore of objects with JavaScript/HTML content containing '); patterns"""
        # Create content that contains "); patterns that could confuse the restore logic
        js_content = """function showAlert() {
    alert("Hello world!");
    console.log("Debug info");
    return true;
}

<script>
    document.addEventListener("DOMContentLoaded", function() {
        console.log("Ready!");
    });
</script>"""

        # Create, backup, delete, restore cycle
        original_obj = TextModel.objects.create(field=js_content)
        original_id = original_obj.id

        connector = SqliteConnector()
        dump = connector.create_dump()

        # Delete the original
        original_obj.delete()
        self.assertFalse(TextModel.objects.filter(id=original_id).exists())

        # Restore and verify
        dump.seek(0)
        connector.restore_dump(dump)

        restored_objects = TextModel.objects.filter(id=original_id)
        self.assertTrue(restored_objects.exists(), "Object should be restored")

        restored_obj = restored_objects.first()
        self.assertEqual(restored_obj.field, js_content, "Content should match exactly")

    def test_restore_dump_may_warn_for_already_exists(self):
        """Test that restore may produce warnings for already existing objects"""
        import warnings

        # Create some test data
        CharModel.objects.create(field="test1")
        TextModel.objects.create(field="test content")

        connector = SqliteConnector()
        dump = connector.create_dump()

        # Clear all data but keep schema (tables/indexes still exist)
        CharModel.objects.all().delete()
        TextModel.objects.all().delete()

        # Restore may produce warnings for already existing schema objects
        dump.seek(0)
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")  # Capture all warnings
            connector.restore_dump(dump)

        # Verify data was restored despite any warnings
        self.assertTrue(CharModel.objects.filter(field="test1").exists())
        self.assertTrue(TextModel.objects.filter(field="test content").exists())

    def test_restore_dump_warns_only_for_serious_errors(self):
        """Test that restore only warns for serious errors like 'no such table'"""
        import warnings
        from io import BytesIO

        # Create a malformed dump with reference to non-existent table
        bad_dump = BytesIO()
        bad_dump.write(b"INSERT INTO nonexistent_table VALUES(1, 'test');\n")
        bad_dump.seek(0)

        connector = SqliteConnector()

        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            connector.restore_dump(bad_dump)

        # Should warn about the serious error
        dbbackup_warnings = [w for w in warning_list if "dbbackup" in str(w.filename)]
        self.assertTrue(len(dbbackup_warnings) > 0, "Should warn about 'no such table' error")

        warning_messages = [str(w.message) for w in dbbackup_warnings]
        self.assertTrue(
            any("no such table" in msg.lower() for msg in warning_messages),
            f"Should warn about 'no such table', got: {warning_messages}",
        )

    def test_create_dump_with_virtual_tables(self):
        with connection.cursor() as c:
            c.execute("CREATE VIRTUAL TABLE lookup USING fts5(field)")

        connector = SqliteConnector()
        dump = connector.create_dump()
        self.assertTrue(dump.read())

    def test_restore_dump_unique_conflict_updates_row(self):
        """
        Test that restoring a dump updates an existing row when a UNIQUE constraint conflict occurs,
        verifying that INSERT OR REPLACE is used to restore the original data.
        """
        # Create initial row
        obj = CharModel.objects.create(field="original")
        obj_id = obj.id
        # Backup
        connector = SqliteConnector()
        dump = connector.create_dump()
        # Modify the existing row so that restoring will cause UNIQUE constraint failure on primary key
        CharModel.objects.filter(id=obj_id).update(field="changed")
        # Restore should update row back to original content via INSERT OR REPLACE retry
        dump.seek(0)
        connector.restore_dump(dump)
        self.assertEqual(CharModel.objects.get(id=obj_id).field, "original")

    def test_schema_objects_use_if_not_exists(self):
        """Test that indexes, triggers, and views use IF NOT EXISTS syntax"""
        from io import BytesIO

        # Create a test table, index, trigger, and view
        with connection.cursor() as c:
            c.execute("CREATE TABLE test_schema (id INTEGER PRIMARY KEY, value TEXT)")
            c.execute("CREATE INDEX test_idx ON test_schema(value)")
            c.execute(
                "CREATE TRIGGER test_trigger AFTER INSERT ON test_schema BEGIN UPDATE test_schema SET value = NEW.value || '_triggered' WHERE id = NEW.id; END"
            )
            c.execute("CREATE VIEW test_view AS SELECT * FROM test_schema WHERE value IS NOT NULL")

        connector = SqliteConnector()
        dump_file = BytesIO()
        connector._write_dump(dump_file)

        # Check that the dump contains IF NOT EXISTS for all schema objects
        dump_content = dump_file.getvalue().decode("utf-8")

        self.assertIn("CREATE INDEX IF NOT EXISTS", dump_content, "Indexes should use IF NOT EXISTS")
        self.assertIn("CREATE TRIGGER IF NOT EXISTS", dump_content, "Triggers should use IF NOT EXISTS")
        self.assertIn("CREATE VIEW IF NOT EXISTS", dump_content, "Views should use IF NOT EXISTS")

    def test_restore_warns_about_already_exists_errors(self):
        """Test that restore warns about 'already exists' errors"""
        import warnings
        from io import BytesIO

        # Create dump content that would trigger "already exists" errors - WITHOUT IF NOT EXISTS
        dump_content = """
CREATE TABLE test_exists (id INTEGER PRIMARY KEY);
CREATE INDEX test_exists_idx ON test_exists(id);
CREATE TRIGGER test_exists_trigger AFTER INSERT ON test_exists BEGIN UPDATE test_exists SET id = NEW.id; END;
CREATE VIEW test_exists_view AS SELECT * FROM test_exists;
        """.strip()

        dump_file = BytesIO(dump_content.encode("utf-8"))
        connector = SqliteConnector()

        # First create the schema objects to ensure "already exists" situations
        with connection.cursor() as c:
            c.execute("CREATE TABLE test_exists (id INTEGER PRIMARY KEY)")
            c.execute("CREATE INDEX test_exists_idx ON test_exists(id)")
            c.execute(
                "CREATE TRIGGER test_exists_trigger AFTER INSERT ON test_exists BEGIN UPDATE test_exists SET id = NEW.id; END"
            )
            c.execute("CREATE VIEW test_exists_view AS SELECT * FROM test_exists")

        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            connector.restore_dump(dump_file)

        # Filter warnings from this package
        dbbackup_warnings = [w for w in warning_list if "dbbackup" in str(w.filename)]

        # Should warn about "already exists" errors now that filtering is removed
        self.assertGreater(len(dbbackup_warnings), 0, "Should have warnings for 'already exists' errors")

        # Verify we get warnings about "already exists"
        already_exists_warnings = [w for w in dbbackup_warnings if "already exists" in str(w.message).lower()]
        self.assertGreater(len(already_exists_warnings), 0, "Should warn about 'already exists' errors")


@patch("dbbackup.db.sqlite.open", mock_open(read_data=b"foo"), create=True)
class SqliteCPConnectorTest(TestCase):
    def test_create_dump(self):
        connector = SqliteCPConnector()
        dump = connector.create_dump()
        dump_content = dump.read()
        self.assertTrue(dump_content)
        self.assertEqual(dump_content, b"foo")

    def test_restore_dump(self):
        connector = SqliteCPConnector()
        dump = connector.create_dump()
        connector.restore_dump(dump)


class SqliteBackupConnectorTest(TestCase):
    def test_create_dump(self):
        connector = SqliteBackupConnector()
        dump = connector.create_dump()
        dump_content = dump.read()
        self.assertTrue(dump_content)
        self.assertTrue(dump_content.startswith(b"SQLite format 3"))

    def test_restore_dump(self):
        connector = SqliteBackupConnector()
        dump = connector.create_dump()
        connector.restore_dump(dump)
