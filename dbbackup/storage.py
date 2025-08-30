"""
Utils for handle files.
"""

import contextlib
import logging

from django.core.exceptions import ImproperlyConfigured

from dbbackup import settings, utils


def get_storage(path=None, options=None):
    """
    Get the specified storage configured with options.

    :param path: Path in Python dot style to module containing the storage
                 class. If empty settings.STORAGES["dbbackup"] will be used.
    :type path: ``str``

    :param options: Parameters for configure the storage, if empty
                    settings.STORAGES["dbbackup"]["OPTIONS"] will be used.
    :type options: ``dict``

    :return: Storage configured
    :rtype: :class:`.Storage`
    """
    path = path or settings.STORAGE
    options = options or settings.STORAGE_OPTIONS
    if not path:
        msg = 'You must specify a storage class using settings.STORAGES["dbbackup"] settings.'
        raise ImproperlyConfigured(msg)
    return Storage(path, **options)


class StorageError(Exception):
    pass


class Storage:
    """
    This object make high-level storage operations for upload/download or
    list and filter files. It uses a Django storage object for low-level
    operations.
    """

    @property
    def logger(self):
        if not hasattr(self, "_logger"):
            self._logger = logging.getLogger("dbbackup.storage")
        return self._logger

    def __init__(self, storage_path=None, **options):
        """
        Initialize a Django Storage instance with given options.

        :param storage_path: Path to a Django Storage class with dot style
                             If ``None``, ``settings.STORAGES["dbbackup"]`` will
                             be used.
        :type storage_path: str
        """
        self._storage_path = storage_path or settings.STORAGE
        options = options.copy()
        options.update(settings.STORAGE_OPTIONS)
        options = {key.lower(): value for key, value in options.items()}
        self.storageCls = get_storage_class(self._storage_path)
        self.storage = self.storageCls(**options)
        self.name = self.storageCls.__name__

    def __str__(self):
        return f"dbbackup-{self.storage.__str__()}"

    def delete_file(self, filepath):
        self.logger.debug("Deleting file %s", filepath)
        self.storage.delete(name=filepath)

    def list_directory(self, path=""):
        return self.storage.listdir(path)[1]

    def write_file(self, filehandle, filename):
        self.logger.debug("Writing file %s", filename)
        self.storage.save(name=filename, content=filehandle)

    def read_file(self, filepath):
        self.logger.debug("Reading file %s", filepath)
        file_ = self.storage.open(name=filepath, mode="rb")
        if not getattr(file_, "name", None):
            file_.name = filepath
        return file_

    def list_backups(
        self,
        encrypted=None,
        compressed=None,
        content_type=None,
        database=None,
        servername=None,
    ):
        """
        List stored files except given filter. If filter is None, it won't be
        used. ``content_type`` must be ``'db'`` for database backups or
        ``'media'`` for media backups.

        :param encrypted: Filter by encrypted or not
        :type encrypted: ``bool`` or ``None``

        :param compressed: Filter by compressed or not
        :type compressed: ``bool`` or ``None``

        :param content_type: Filter by media or database backup, must be
                             ``'db'`` or ``'media'``

        :type content_type: ``str`` or ``None``

        :param database: Filter by source database's name
        :type: ``str`` or ``None``

        :param servername: Filter by source server's name
        :type: ``str`` or ``None``

        :returns: List of files
        :rtype: ``list`` of ``str``
        """
        if content_type not in ("db", "media", None):
            msg = f"Bad content_type {content_type}, must be 'db', 'media', or None"
            raise TypeError(msg)
        # TODO: Make better filter for include only backups
        files = [f for f in self.list_directory() if utils.filename_to_datestring(f)]
        if encrypted is not None:
            files = [f for f in files if (".gpg" in f) == encrypted]
        if compressed is not None:
            files = [f for f in files if (".gz" in f) == compressed]
        if content_type == "media":
            files = [f for f in files if ".tar" in f]
        elif content_type == "db":
            files = [f for f in files if ".tar" not in f]
        if database:
            files = [f for f in files if database in f]
        if servername:
            files = [f for f in files if servername in f]
        return files

    def get_latest_backup(
        self,
        encrypted=None,
        compressed=None,
        content_type=None,
        database=None,
        servername=None,
    ):
        """
        Return the latest backup file name.

        :param encrypted: Filter by encrypted or not
        :type encrypted: ``bool`` or ``None``

        :param compressed: Filter by compressed or not
        :type compressed: ``bool`` or ``None``

        :param content_type: Filter by media or database backup, must be
                             ``'db'`` or ``'media'``

        :type content_type: ``str`` or ``None``

        :param database: Filter by source database's name
        :type: ``str`` or ``None``

        :param servername: Filter by source server's name
        :type: ``str`` or ``None``

        :returns: Most recent file
        :rtype: ``str``

        :raises: FileNotFound: If no backup file is found
        """
        files = self.list_backups(
            encrypted=encrypted,
            compressed=compressed,
            content_type=content_type,
            database=database,
            servername=servername,
        )
        if not files:
            msg = "There's no backup file available."
            raise StorageError(msg)
        return max(files, key=utils.filename_to_date)

    def get_older_backup(
        self,
        encrypted=None,
        compressed=None,
        content_type=None,
        database=None,
        servername=None,
    ):
        """
        Return the older backup's file name.

        :param encrypted: Filter by encrypted or not
        :type encrypted: ``bool`` or ``None``

        :param compressed: Filter by compressed or not
        :type compressed: ``bool`` or ``None``

        :param content_type: Filter by media or database backup, must be
                             ``'db'`` or ``'media'``

        :type content_type: ``str`` or ``None``

        :param database: Filter by source database's name
        :type: ``str`` or ``None``

        :param servername: Filter by source server's name
        :type: ``str`` or ``None``

        :returns: Older file
        :rtype: ``str``

        :raises: FileNotFound: If no backup file is found
        """
        files = self.list_backups(
            encrypted=encrypted,
            compressed=compressed,
            content_type=content_type,
            database=database,
            servername=servername,
        )
        if not files:
            msg = "There's no backup file available."
            raise StorageError(msg)
        return min(files, key=utils.filename_to_date)

    def clean_old_backups(
        self,
        encrypted=None,
        compressed=None,
        content_type=None,
        database=None,
        servername=None,
        keep_number=None,
    ):
        """
        Delete olders backups and hold the number defined.

        :param encrypted: Filter by encrypted or not
        :type encrypted: ``bool`` or ``None``

        :param compressed: Filter by compressed or not
        :type compressed: ``bool`` or ``None``

        :param content_type: Filter by media or database backup, must be
                             ``'db'`` or ``'media'``

        :type content_type: ``str`` or ``None``

        :param database: Filter by source database's name
        :type: ``str`` or ``None``

        :param servername: Filter by source server's name
        :type: ``str`` or ``None``

        :param keep_number: Number of files to keep, other will be deleted
        :type keep_number: ``int`` or ``None``
        """
        if keep_number is None:
            keep_number = settings.CLEANUP_KEEP if content_type == "db" else settings.CLEANUP_KEEP_MEDIA
        keep_filter = settings.CLEANUP_KEEP_FILTER
        files = self.list_backups(
            encrypted=encrypted,
            compressed=compressed,
            content_type=content_type,
            database=database,
            servername=servername,
        )
        files = sorted(files, key=utils.filename_to_date, reverse=True)
        files_to_delete = [fi for i, fi in enumerate(files) if i >= keep_number]
        for filename in files_to_delete:
            if keep_filter(filename):
                continue
            self.delete_file(filename)


def get_storage_class(path=None):
    """
    Return the configured storage class.

    :param path: Path in Python dot style to module containing the storage
                    class. If empty, the default storage class will be used.
    :type path: str or None

    :returns: Storage class
    :rtype: :class:`django.core.files.storage.Storage`
    """
    from django.utils.module_loading import import_string

    if path:
        # this is a workaround to keep compatibility with Django >= 5.1 (django.core.files.storage.get_storage_class is removed)
        return import_string(path)

    with contextlib.suppress(Exception):
        from django.core.files.storage import DefaultStorage

        return DefaultStorage

    from django.core.files.storage import get_storage_class

    return get_storage_class()
