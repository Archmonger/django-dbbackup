"""
Restore media files.
"""

import tarfile

from dbbackup import utils
from dbbackup.management.commands._base import BaseDbBackupCommand, make_option
from dbbackup.signals import post_media_restore, pre_media_restore
from dbbackup.storage import get_storage, get_storage_class


class Command(BaseDbBackupCommand):
    help = """Restore a media backup from storage, encrypted and/or
    compressed."""
    content_type = "media"

    option_list = (
        make_option(
            "-i",
            "--input-filename",
            action="store",
            help="Specify filename to backup from",
        ),
        make_option("-I", "--input-path", help="Specify path on local filesystem to backup from"),
        make_option(
            "-s",
            "--servername",
            help="If backup file is not specified, filter the existing ones with the given servername",
        ),
        make_option(
            "-e",
            "--decrypt",
            default=False,
            action="store_true",
            help="Decrypt data before restoring",
        ),
        make_option("-p", "--passphrase", default=None, help="Passphrase for decrypt file"),
        make_option(
            "-z",
            "--uncompress",
            action="store_true",
            help="Uncompress gzip data before restoring",
        ),
        make_option("-r", "--replace", help="Replace existing files", action="store_true"),
    )

    def handle(self, *args, **options):
        """Django command handler."""
        self.verbosity = int(options.get("verbosity"))
        self.quiet = options.get("quiet")
        self._set_logger_level()

        self.servername = options.get("servername")
        self.decrypt = options.get("decrypt")
        self.uncompress = options.get("uncompress")

        self.filename = options.get("input_filename")
        self.path = options.get("input_path")

        self.replace = options.get("replace")
        self.passphrase = options.get("passphrase")
        self.interactive = options.get("interactive")

        self.storage = get_storage()
        self.media_storage = get_storage_class()()
        self._restore_backup()

    def _upload_file(self, name, media_file):
        if self.media_storage.exists(name):
            if not self.replace:
                return
            self.media_storage.delete(name)
            self.logger.info("%s deleted", name)
        self.media_storage.save(name, media_file)
        self.logger.info("%s uploaded", name)

    def _restore_backup(self):
        self.logger.info("Restoring backup for media files")
        input_filename, input_file = self._get_backup_file(servername=self.servername)
        self.logger.info("Restoring: %s", input_filename)

        # Send pre_media_restore signal
        pre_media_restore.send(
            sender=self.__class__,
            filename=input_filename,
            servername=self.servername,
            storage=self.storage,
        )

        if self.decrypt:
            unencrypted_file, input_filename = utils.unencrypt_file(input_file, input_filename, self.passphrase)
            input_file.close()
            input_file = unencrypted_file

        self.logger.debug("Backup size: %s", utils.handle_size(input_file))
        if self.interactive:
            self._ask_confirmation()

        input_file.seek(0)
        tar_file = (
            tarfile.open(fileobj=input_file, mode="r:gz")
            if self.uncompress
            else tarfile.open(fileobj=input_file, mode="r:")
        )
        # Restore file 1 by 1
        for media_file_info in tar_file:
            if media_file_info.path == "media":
                continue  # Don't copy root directory
            media_file = tar_file.extractfile(media_file_info)
            if media_file is None:
                continue  # Skip directories
            name = media_file_info.path
            self._upload_file(name, media_file)

        # Send post_media_restore signal
        post_media_restore.send(
            sender=self.__class__,
            filename=input_filename,
            servername=self.servername,
            storage=self.storage,
        )
