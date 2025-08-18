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

    def test_restore_dump_no_warnings_for_clean_database(self):
        """Test that restore produces no warnings when restoring to a clean database"""
        import warnings

        # Create some test data
        CharModel.objects.create(field="test1")
        TextModel.objects.create(field="test content")

        connector = SqliteConnector()
        dump = connector.create_dump()

        # Clear all data
        CharModel.objects.all().delete()
        TextModel.objects.all().delete()

        # Restore should produce no warnings
        dump.seek(0)
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")  # Capture all warnings
            connector.restore_dump(dump)

        # Filter out warnings from this package only
        dbbackup_warnings = [w for w in warning_list if "dbbackup" in str(w.filename)]
        self.assertEqual(
            len(dbbackup_warnings), 0, f"Expected no warnings, but got: {[str(w.message) for w in dbbackup_warnings]}"
        )

        # Verify data was restored
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
