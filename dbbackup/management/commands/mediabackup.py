"""
Save media files.
"""

import os
import tarfile

from django.core.management.base import CommandError

from dbbackup import utils
from dbbackup.management.commands._base import BaseDbBackupCommand, make_option
from dbbackup.signals import post_media_backup, pre_media_backup
from dbbackup.storage import StorageError, get_storage, get_storage_class


class Command(BaseDbBackupCommand):
    help = """Backup media files, gather all in a tarball and encrypt or
    compress."""
    content_type = "media"

    option_list = (
        *BaseDbBackupCommand.option_list,
        make_option("-c", "--clean", help="Clean up old backup files", action="store_true", default=False),
        make_option("-s", "--servername", help="Specify server name to include in backup filename"),
        make_option("-z", "--compress", help="Compress the archive", action="store_true", default=False),
        make_option("-e", "--encrypt", help="Encrypt the backup files", action="store_true", default=False),
        make_option("-o", "--output-filename", default=None, help="Specify filename on storage"),
        make_option(
            "-O",
            "--output-path",
            default=None,
            help="Specify where to store backup (local filesystem path or S3 URI like s3://bucket/path/)",
        ),
    )

    @utils.email_uncaught_exception
    def handle(self, **options):
        self.verbosity = options.get("verbosity")
        self.quiet = options.get("quiet")
        self._set_logger_level()

        self.encrypt = options.get("encrypt", False)
        self.compress = options.get("compress", False)
        self.servername = options.get("servername")

        self.filename = options.get("output_filename")
        self.path = options.get("output_path")
        try:
            self.media_storage = get_storage_class()()
            self.storage = get_storage()
            self.backup_mediafiles()
            if options.get("clean"):
                self._cleanup_old_backups(servername=self.servername)

        except StorageError as err:
            raise CommandError(err) from err

    def _explore_storage(self):
        """Generator of all files contained in media storage."""
        path = ""
        dirs = [path]
        while dirs:
            path = dirs.pop()
            subdirs, files = self.media_storage.listdir(path)
            for media_filename in files:
                yield os.path.join(path, media_filename)
            dirs.extend([os.path.join(path, subdir) for subdir in subdirs])

    def _create_tar(self, name):
        """Create TAR file."""
        fileobj = utils.create_spooled_temporary_file()
        mode = "w:gz" if self.compress else "w"
        tar_file = tarfile.open(name=name, fileobj=fileobj, mode=mode)
        for media_filename in self._explore_storage():
            tarinfo = tarfile.TarInfo(media_filename)
            media_file = self.media_storage.open(media_filename)
            tarinfo.size = len(media_file)
            tar_file.addfile(tarinfo, media_file)
        # Close the TAR for writing
        tar_file.close()
        return fileobj

    def backup_mediafiles(self):
        """
        Create backup file and write it to storage.
        """
        # Send pre_media_backup signal
        pre_media_backup.send(
            sender=self.__class__,
            servername=self.servername,
            storage=self.storage,
        )

        # Check for filename option
        if self.filename:
            filename = self.filename
        else:
            extension = f"tar{'.gz' if self.compress else ''}"
            filename = utils.filename_generate(extension, servername=self.servername, content_type=self.content_type)

        tarball = self._create_tar(filename)
        # Apply trans
        if self.encrypt:
            encrypted_file = utils.encrypt_file(tarball, filename)
            tarball, filename = encrypted_file

        self.logger.debug("Backup size: %s", utils.handle_size(tarball))
        # Store backup
        tarball.seek(0)
        if self.path is None:
            self.write_to_storage(tarball, filename)
        elif self.path.startswith("s3://"):
            # Handle S3 URIs through storage backend
            self.write_to_storage(tarball, self.path)
        else:
            self.write_local_file(tarball, self.path)

        # Send post_media_backup signal
        post_media_backup.send(
            sender=self.__class__,
            filename=filename,
            servername=self.servername,
            storage=self.storage,
        )
