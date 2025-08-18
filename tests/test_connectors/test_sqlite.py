from io import BytesIO
from unittest.mock import mock_open, patch

from django.db import connection
from django.test import TestCase

from dbbackup.db.sqlite import SqliteConnector, SqliteCPConnector, SqliteBackupConnector
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
        TextModel.objects.create(
            field=f'INSERT ({"foo" * 5000}\nbar\n WHERE \nbaz IS\n "great" );\n'
        )

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
        js_content = '''function showAlert() {
    alert("Hello world!");
    console.log("Debug info");
    return true;
}

<script>
    document.addEventListener("DOMContentLoaded", function() {
        console.log("Ready!");
    });
</script>'''
        
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
