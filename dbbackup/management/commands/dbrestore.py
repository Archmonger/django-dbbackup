"""
Restore database.
"""

import io
import json
import os
import sys
from importlib import import_module

from django.conf import settings
from django.core.management.base import CommandError
from django.db import connection

from dbbackup import utils
from dbbackup.db.base import get_connector
from dbbackup.management.commands._base import BaseDbBackupCommand, make_option
from dbbackup.signals import post_restore, pre_restore
from dbbackup.storage import StorageError, get_storage


class Command(BaseDbBackupCommand):
    help = "Restore a database backup from storage, encrypted and/or compressed."
    content_type = "db"
    no_drop = False
    pg_options = ""
    input_database_name = None
    database_name = None
    database = None

    option_list = (
        *BaseDbBackupCommand.option_list,
        make_option("-d", "--database", help="Database to restore"),
        make_option("-i", "--input-filename", help="Specify filename to backup from"),
        make_option("-I", "--input-path", help="Specify path on local filesystem to backup from"),
        make_option(
            "-s",
            "--servername",
            help="If backup file is not specified, filter the existing ones with the given servername",
        ),
        make_option("-c", "--decrypt", default=False, action="store_true", help="Decrypt data before restoring"),
        make_option("-p", "--passphrase", help="Passphrase for decrypt file", default=None),
        make_option(
            "-z", "--uncompress", action="store_true", default=False, help="Uncompress gzip data before restoring"
        ),
        make_option(
            "-n",
            "--schema",
            action="append",
            default=[],
            help="Specify schema(s) to restore. Can be used multiple times.",
        ),
        make_option(
            "-r",
            "--no-drop",
            action="store_true",
            default=False,
            help="Don't clean (drop) the database. This only works with mongodb and postgresql.",
        ),
        make_option(
            "--pg-options",
            dest="pg_options",
            default="",
            help="Additional pg_restore options, e.g. '--if-exists --no-owner'. Use quotes.",
        ),
    )

    def handle(self, *args, **options):
        """Django command handler."""
        self.verbosity = int(options.get("verbosity"))
        self.quiet = options.get("quiet")
        self._set_logger_level()

        try:
            connection.close()
            self.filename = options.get("input_filename")
            self.path = options.get("input_path")
            self.servername = options.get("servername")
            self.decrypt = options.get("decrypt")
            self.uncompress = options.get("uncompress")
            self.passphrase = options.get("passphrase")
            self.interactive = options.get("interactive")
            self.input_database_name = options.get("database")
            self.database_name, self.database = self._get_database(self.input_database_name)
            self.storage = get_storage()
            self.no_drop = options.get("no_drop")
            self.pg_options = options.get("pg_options", "")
            self.schemas = options.get("schema")
            self._restore_backup()
        except StorageError as err:
            raise CommandError(err) from err

    def _get_database(self, database_name: str):
        """Get the database to restore."""
        if not database_name:
            if len(settings.DATABASES) > 1:
                errmsg = "Because this project contains more than one database, you must specify the --database option."
                raise CommandError(errmsg)
            database_name = next(iter(settings.DATABASES.keys()))
        if database_name not in settings.DATABASES:
            msg = f"Database {database_name} does not exist."
            raise CommandError(msg)
        return database_name, settings.DATABASES[database_name]

    def _check_metadata(self, filename):
        """
        Check if the backup file has metadata and if it matches the current database.
        """
        metadata_filename = f"{filename}.metadata"
        metadata = None

        if self.path:
            # Local file
            # self.path is the full path to the backup file
            metadata_path = f"{self.path}.metadata"
            if os.path.exists(metadata_path):
                with open(metadata_path) as fd:
                    metadata = json.load(fd)
        else:
            # Storage file
            try:
                # Check if metadata file exists in storage
                # list_directory returns a list of filenames
                # We can't easily check existence without listing or trying to open
                # But read_file might fail if not exists depending on storage
                # Let's try to read it
                metadata_file = self.storage.read_file(metadata_filename)
            except Exception:
                self.logger.debug("No metadata file found for '%s'", filename)
                return None

            # Read and parse metadata
            try:
                metadata = json.load(metadata_file)
            except Exception:
                self.logger.warning(
                    "Malformatted metadata file for '%s'! Dbbackup will ignore this metadata.", filename
                )
                return None

        if not metadata:
            return None

        backup_engine = metadata.get("engine")
        current_engine = settings.DATABASES[self.database_name]["ENGINE"]
        backup_connector = metadata.get("connector")

        if backup_engine != current_engine and backup_connector != "dbbackup.db.django.DjangoConnector":
            msg = (
                f"Backup file '{filename}' was created with database engine '{backup_engine}', "
                f"but you are restoring to a database using '{current_engine}'. "
                "Restoring to a different database engine is not supported."
            )
            raise CommandError(msg)

        return metadata

    def _restore_backup(self):
        """Restore the specified database."""
        input_filename, input_file = self._get_backup_file(
            database=self.input_database_name, servername=self.servername
        )

        self.logger.info(
            "Restoring backup for database '%s' and server '%s'",
            self.database_name,
            self.servername,
        )

        if self.schemas:
            self.logger.info(f"Restoring schemas: {self.schemas}")  # noqa: G004

        self.logger.info(f"Restoring: {input_filename}")  # noqa: G004

        metadata = self._check_metadata(input_filename)

        # Send pre_restore signal
        pre_restore.send(
            sender=self.__class__,
            database=self.database,
            database_name=self.database_name,
            filename=input_filename,
            servername=self.servername,
            storage=self.storage,
        )

        if self.decrypt:
            unencrypted_file, input_filename = utils.unencrypt_file(input_file, input_filename, self.passphrase)
            input_file.close()
            input_file = unencrypted_file
        if self.uncompress:
            uncompressed_file, input_filename = utils.uncompress_file(input_file, input_filename)
            input_file.close()
            input_file = uncompressed_file

        # Convert remote storage files to SpooledTemporaryFile for compatibility with subprocess
        # This fixes the issue with FTP and other remote storage backends that don't support fileno()
        if not self.path:  # Only for remote storage files, not local files
            try:
                # Test if the file supports fileno() - required by subprocess.Popen
                input_file.fileno()
            except (AttributeError, io.UnsupportedOperation):
                # File doesn't support fileno(), convert to SpooledTemporaryFile
                self.logger.debug(
                    "Converting remote storage file to temporary file due to missing fileno() support required by subprocess"
                )
                temp_file = utils.create_spooled_temporary_file(fileobj=input_file)
                input_file.close()
                input_file = temp_file

        self.logger.info("Restore tempfile created: %s", utils.handle_size(input_file))
        if self.interactive:
            self._ask_confirmation()

        input_file.seek(0)

        # Try to use connector from metadata if available
        self.connector = None
        if metadata and "connector" in metadata:
            connector_path = metadata["connector"]
            try:
                module_name = ".".join(connector_path.split(".")[:-1])
                class_name = connector_path.split(".")[-1]
                module = import_module(module_name)
                connector_class = getattr(module, class_name)
                self.connector = connector_class(self.database_name)
                self.logger.info("Using connector from metadata: '%s'", connector_path)
            except (ImportError, AttributeError):
                self.logger.warning(
                    "Connector '%s' from metadata not found!!! Falling back to the connector in your Django settings.",
                    connector_path,
                )
                if self.interactive:
                    answer = input("Do you want to continue with the connector defined in your Django settings? [Y/n] ")
                    if not answer.lower().startswith("y"):
                        self.logger.info("Quitting")
                        sys.exit(0)

        # Fallback to a connector from Django settings and/or our default connector map.
        if not self.connector:
            self.connector = get_connector(self.database_name)

        if self.schemas:
            self.connector.schemas = self.schemas
        self.connector.drop = not self.no_drop
        self.connector.pg_options = self.pg_options
        self.connector.restore_dump(input_file)

        # Send post_restore signal
        post_restore.send(
            sender=self.__class__,
            database=self.database,
            database_name=self.database_name,
            filename=input_filename,
            servername=self.servername,
            connector=self.connector,
            storage=self.storage,
        )
