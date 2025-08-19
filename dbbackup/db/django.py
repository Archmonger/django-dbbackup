"""
Django native serializer connector for database backup and restore.

This connector uses Django's built-in dumpdata and loaddata commands
for database-agnostic backup and restore operations. It works with
any Django-supported database backend.
"""

import tempfile
import os
from io import StringIO
from tempfile import SpooledTemporaryFile

from django.core.management import call_command
from django.core.files.base import File

from .base import BaseDBConnector


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
        # Use StringIO to capture the output
        output = StringIO()

        # Prepare arguments for dumpdata command
        dump_args = []
        dump_kwargs = {
            "format": "json",
            "stdout": output,
            "verbosity": 0,
            "use_natural_foreign_keys": True,
            "use_natural_primary_keys": True,
        }

        # Handle exclude parameter if specified
        if self.exclude:
            dump_kwargs["exclude"] = [f"{app}.{model}" for app in self.exclude for model in ["*"]]
            # If exclude contains table names, convert them to app.model format
            # For now, we'll pass exclude as-is since dumpdata expects app.model format
            # This might need refinement based on how exclude is typically used
            if all("." not in item for item in self.exclude):
                # If exclude items don't contain dots, they're likely table names
                # We'll exclude them by app label (this is a best-effort conversion)
                pass  # For now, we'll handle this in a future iteration

        # Run dumpdata command
        call_command("dumpdata", *dump_args, **dump_kwargs)

        # Get the JSON content and create a file-like object
        json_content = output.getvalue()

        # Create a SpooledTemporaryFile to return
        dump_file = SpooledTemporaryFile(mode="w+b")
        dump_file.write(json_content.encode("utf-8"))
        dump_file.seek(0)

        return dump_file

    def _restore_dump(self, dump):
        """
        Restore a database dump using Django's loaddata command.

        Args:
            dump: File-like object containing JSON fixture data
        """
        # Create a temporary file for loaddata to read from
        with tempfile.NamedTemporaryFile(mode="w+b", suffix=".json", delete=False) as temp_file:
            # Copy dump content to temporary file
            if isinstance(dump, File):
                dump.seek(0)
                content = dump.read()
                if isinstance(content, str):
                    content = content.encode("utf-8")
                temp_file.write(content)
            else:
                dump.seek(0)
                content = dump.read()
                if isinstance(content, str):
                    content = content.encode("utf-8")
                temp_file.write(content)

            temp_file_path = temp_file.name

        try:
            # Run loaddata command
            call_command("loaddata", temp_file_path, verbosity=0)
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass  # Best effort cleanup
