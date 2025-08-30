"""
Django native serializer connector for database backup and restore.

This connector uses Django's built-in dumpdata and loaddata commands
for database-agnostic backup and restore operations. It works with
any Django-supported database backend.
"""

import contextlib
import os
import tempfile
from tempfile import SpooledTemporaryFile

from django.core.management import call_command

from dbbackup.db.base import BaseDBConnector


class DjangoConnector(BaseDBConnector):
    """
    Django native connector that uses dumpdata/loaddata commands.

    This connector provides database-agnostic backup and restore functionality
    by leveraging Django's built-in serialization system. It supports any
    database backend that Django supports and handles model-level backups
    with proper foreign key relationships preserved.
    """

    extension = "json"

    def _create_dump(self):
        """
        Create a database dump using Django's dumpdata command.

        Returns a file-like object containing the serialized database data
        in JSON format.
        """
        # Create a SpooledTemporaryFile in text mode for direct use with dumpdata
        dump_file = SpooledTemporaryFile(mode="w+t", encoding="utf-8")

        # Prepare arguments for dumpdata command
        dump_args = []
        dump_kwargs = {
            "format": "json",
            "stdout": dump_file,
            "verbosity": 0,
            "use_natural_foreign_keys": True,
            "use_natural_primary_keys": True,
        }

        # Handle exclude parameter if specified
        if self.exclude:
            exclude_list = []
            for item in self.exclude:
                if "." in item:
                    # Already in app.model format - validate it exists before adding
                    # Skip invalid app.model combinations silently
                    # This allows for graceful handling of non-existent models
                    with contextlib.suppress(LookupError, ValueError):
                        from django.apps import apps

                        app_label, model_name = item.split(".", 1)
                        apps.get_model(app_label, model_name)
                        exclude_list.append(item)
                else:
                    # Handle table name format - convert only well-known Django patterns
                    # For unknown table names, skip them rather than risk errors
                    converted = None
                    if item.startswith("auth_"):
                        # Handle Django auth tables (only if auth app is available)
                        with contextlib.suppress(LookupError):
                            from django.apps import apps

                            apps.get_app_config("auth")  # Check if auth app exists
                            model_name = item[5:]  # Remove 'auth_' prefix
                            if model_name == "group":
                                converted = "auth.Group"
                            elif model_name == "permission":
                                converted = "auth.Permission"
                            elif model_name == "user":
                                converted = "auth.User"
                    elif item.startswith("django_"):
                        # Handle Django internal tables (only if apps are available)
                        model_name = item[7:]  # Remove 'django_' prefix
                        # Required app not installed, skip
                        with contextlib.suppress(LookupError):
                            from django.apps import apps

                            if model_name == "admin_log":
                                apps.get_app_config("admin")
                                converted = "admin.LogEntry"
                            elif model_name == "content_type":
                                apps.get_app_config("contenttypes")
                                converted = "contenttypes.ContentType"
                            elif model_name == "session":
                                apps.get_app_config("sessions")
                                converted = "sessions.Session"
                    # Only add converted names that we're confident about
                    # For unknown table names, we skip them to avoid Django validation errors
                    # This is safer than trying to guess the correct app.model format
                    if converted:
                        exclude_list.append(converted)

            if exclude_list:
                dump_kwargs["exclude"] = exclude_list

        # Run dumpdata command - this streams directly to the text file
        call_command("dumpdata", *dump_args, **dump_kwargs)

        # Reset file position to beginning for reading
        dump_file.seek(0)
        return dump_file

    def _restore_dump(self, dump):
        """
        Restore a database dump using Django's loaddata command.

        Args:
            dump: File-like object containing JSON fixture data
        """
        # Create a temporary file for loaddata to read from
        with tempfile.NamedTemporaryFile(mode="w+t", suffix=".json", encoding="utf-8", delete=False) as temp_file:
            # Stream copy dump content to temporary file to avoid loading everything into memory
            dump.seek(0)
            # Use chunked reading for memory efficiency
            while True:
                chunk = dump.read(8192)  # 8KB chunks
                if not chunk:
                    break
                if isinstance(chunk, bytes):
                    chunk = chunk.decode("utf-8")
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        try:
            # Run loaddata command
            call_command("loaddata", temp_file_path, verbosity=0)
        finally:
            # Best effort clean-up of temporary file
            with contextlib.suppress(OSError):
                os.unlink(temp_file_path)
