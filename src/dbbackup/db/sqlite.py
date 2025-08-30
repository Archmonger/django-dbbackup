import contextlib
import os
import sqlite3
import warnings
from io import BytesIO
from shutil import copyfileobj
from tempfile import NamedTemporaryFile, SpooledTemporaryFile

from django.db import IntegrityError, OperationalError

from dbbackup.db.base import BaseDBConnector

DUMP_TABLES = """
SELECT "name", "type", "sql"
FROM "sqlite_master"
WHERE "sql" NOT NULL AND "type" == 'table'
ORDER BY "name"
"""
DUMP_ETC = """
SELECT "name", "type", "sql"
FROM "sqlite_master"
WHERE "sql" NOT NULL AND "type" IN ('index', 'trigger', 'view')
"""


class SqliteConnector(BaseDBConnector):
    """
    Create a dump at SQL layer like could make ``.dumps`` in sqlite3.
    Restore by evaluate the created SQL.
    """

    def _write_dump(self, fileobj):
        cursor = self.connection.cursor()
        cursor.execute(DUMP_TABLES)
        for table_name, _, sql in cursor.fetchall():
            if table_name.startswith("sqlite_") or table_name in self.exclude:
                continue
            if sql.startswith("CREATE TABLE"):
                sql = sql.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS")
                # Make SQL commands in 1 line
                sql = sql.replace("\n    ", "")
                sql = sql.replace("\n)", ")")
            fileobj.write(f"{sql};\n".encode())

            table_name_ident = table_name.replace('"', '""')
            cursor.execute(f'PRAGMA table_info("{table_name_ident}")')
            column_names = [str(table_info[1]) for table_info in cursor.fetchall()]
            q = """SELECT 'INSERT OR REPLACE INTO "{0}" VALUES({1})' FROM "{0}";\n""".format(
                table_name_ident,
                ",".join(f"""'||quote("{col.replace('"', '""')}")||'""" for col in column_names),
            )
            cursor.execute(q)
            for row in cursor:
                fileobj.write(f"{row[0]};\n".encode())

        # Dump indexes, triggers, and views after all tables are created
        cursor.execute(DUMP_ETC)
        for _name, _, sql in cursor.fetchall():
            if sql.startswith("CREATE INDEX"):
                sql = sql.replace("CREATE INDEX", "CREATE INDEX IF NOT EXISTS", 1)
            elif sql.startswith("CREATE TRIGGER"):
                sql = sql.replace("CREATE TRIGGER", "CREATE TRIGGER IF NOT EXISTS", 1)
            elif sql.startswith("CREATE VIEW"):
                sql = sql.replace("CREATE VIEW", "CREATE VIEW IF NOT EXISTS", 1)
            fileobj.write(f"{sql};\n".encode())
        cursor.close()

    def create_dump(self):
        if not self.connection.is_usable():
            self.connection.connect()
        dump_file = SpooledTemporaryFile(max_size=10 * 1024 * 1024)
        self._write_dump(dump_file)
        dump_file.seek(0)
        return dump_file

    def _is_sql_command_complete(self, sql_command_bytes):
        """
        Check if an SQL command is complete by ensuring that any closing ");\n"
        is not within a quoted string literal.
        """
        sql_str = sql_command_bytes.decode("UTF-8")
        if not sql_str.endswith(");\n"):
            return False

        # Parse the SQL to check if we're inside a quoted string at the end
        in_quotes = False
        i = 0
        while i < len(sql_str) - 3:  # -3 to avoid checking the final ");\n"
            char = sql_str[i]
            if char == "'":
                if i + 1 < len(sql_str) and sql_str[i + 1] == "'":
                    # Escaped single quote (''), skip both
                    i += 2
                else:
                    # Toggle quote state
                    in_quotes = not in_quotes
                    i += 1
            else:
                i += 1

        # The command is complete if we're not inside quotes when we reach ");\n"
        return not in_quotes

    def restore_dump(self, dump):
        if not self.connection.is_usable():
            self.connection.connect()
        cursor = self.connection.cursor()
        sql_command = b""
        sql_is_complete = True
        for line in dump.readlines():
            sql_command = sql_command + line
            line_str = line.decode("UTF-8")
            if line_str.startswith("INSERT") and not line_str.endswith(");\n"):
                sql_is_complete = False
                continue
            if not sql_is_complete:
                # Check if the accumulated command is now complete
                sql_is_complete = self._is_sql_command_complete(sql_command)

            if sql_is_complete:
                try:
                    cursor.execute(sql_command.decode("UTF-8"))
                except (OperationalError, IntegrityError) as err:
                    err_str = str(err)
                    if not self._should_suppress_error(err_str):
                        warnings.warn(f"Error in db restore: {err}")

                sql_command = b""

    @staticmethod
    def _should_suppress_error(msg: str):
        return (msg.startswith(("index", "trigger", "view"))) and msg.endswith("already exists")


class SqliteCPConnector(BaseDBConnector):
    """
    Create a dump by copy the binary data file.
    Restore by simply copy to the good location.
    """

    def create_dump(self):
        path = self.connection.settings_dict["NAME"]
        dump = BytesIO()
        with open(path, "rb") as db_file:
            copyfileobj(db_file, dump)
        dump.seek(0)
        return dump

    def restore_dump(self, dump):
        path = self.connection.settings_dict["NAME"]
        with open(path, "wb") as db_file:
            copyfileobj(dump, db_file)


class SqliteBackupConnector(BaseDBConnector):
    """
    Create a dump using the SQLite backup command,
    which is safe to execute when the database is
    in use (unlike simply copying the database file).
    Restore by copying the backup file over the
    database file.
    """

    extension = "sqlite3"

    def _write_dump(self, fileobj):
        pass

    def create_dump(self):
        if not self.connection.is_usable():
            self.connection.connect()
        # Important: ensure the connection to the DB
        # has been established.
        self.connection.ensure_connection()
        src_db_connection = self.connection.connection

        # On Windows sqlite3 cannot open a NamedTemporaryFile that is still
        # open by another handle. Use delete=False then reopen.
        bkp_db_file = NamedTemporaryFile(delete=False)
        bkp_path = bkp_db_file.name
        bkp_db_file.close()  # Close so sqlite can open it on Windows.
        try:
            with sqlite3.connect(bkp_path) as bkp_db_connection:
                src_db_connection.backup(bkp_db_connection)
            with open(bkp_path, "rb") as reopened:
                spooled = SpooledTemporaryFile()
                copyfileobj(reopened, spooled)
            spooled.seek(0)
            return spooled
        finally:  # pragma: no cover - cleanup best effort
            with contextlib.suppress(Exception):
                os.remove(bkp_path)

    def restore_dump(self, dump):
        path = self.connection.settings_dict["NAME"]
        with open(path, "wb") as db_file:
            copyfileobj(dump, db_file)
