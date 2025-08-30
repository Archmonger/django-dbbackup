"""
Utility functions for dbbackup.
"""

import gzip
import logging
import os
import re
import sys
import tempfile
import traceback
from datetime import datetime
from functools import wraps
from getpass import getpass
from shutil import copyfileobj

from django.core.mail import EmailMultiAlternatives
from django.db import connection
from django.http import HttpRequest
from django.utils import timezone

from dbbackup import settings

FAKE_HTTP_REQUEST = HttpRequest()
FAKE_HTTP_REQUEST.META["SERVER_NAME"] = ""
FAKE_HTTP_REQUEST.META["SERVER_PORT"] = ""
FAKE_HTTP_REQUEST.META["HTTP_HOST"] = settings.HOSTNAME
FAKE_HTTP_REQUEST.path = "/DJANGO-DBBACKUP-EXCEPTION"

BYTES = (
    ("PiB", 1125899906842624.0),
    ("TiB", 1099511627776.0),
    ("GiB", 1073741824.0),
    ("MiB", 1048576.0),
    ("KiB", 1024.0),
    ("B", 1.0),
)

REG_FILENAME_CLEAN = re.compile(r"-+")


class EncryptionError(Exception):
    pass


class DecryptionError(Exception):
    pass


def bytes_to_str(byte_val, decimals=1):
    """
    Convert bytes to a human readable string.

    :param byteVal: Value to convert in bytes
    :type byteVal: int or float

    :param decimal: Number of decimal to display
    :type decimal: int

    :returns: Number of byte with the best unit of measure
    :rtype: str
    """
    for unit, byte in BYTES:
        if byte_val >= byte:
            if decimals == 0:
                return f"{int(round(byte_val / byte, 0))} {unit}"
            return f"{round(byte_val / byte, decimals)} {unit}"
    return f"{byte_val} B"


def handle_size(filehandle):
    """
    Get file's size to a human readable string.

    :param filehandle: File to handle
    :type filehandle: file

    :returns: File's size with the best unit of measure
    :rtype: str
    """
    if hasattr(filehandle, "size"):
        return bytes_to_str(filehandle.size)

    filehandle.seek(0, 2)
    return bytes_to_str(filehandle.tell())


def mail_admins(subject, message, fail_silently=False, connection=None, html_message=None):
    """Sends a message to the admins, as defined by the DBBACKUP_ADMINS setting."""
    if not settings.ADMINS:
        return
    mail = EmailMultiAlternatives(
        f"{settings.EMAIL_SUBJECT_PREFIX}{subject}",
        message,
        settings.SERVER_EMAIL,
        [a[1] for a in settings.ADMINS],
        connection=connection,
    )

    if html_message:
        mail.attach_alternative(html_message, "text/html")
    mail.send(fail_silently=fail_silently)


def email_uncaught_exception(func):
    """
    Function decorator for send email with uncaught exceptions to admins.
    Email is sent to ``settings.DBBACKUP_FAILURE_RECIPIENTS``
    (``settings.ADMINS`` if not defined). The message contains a traceback
    of error.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception:
            logger = logging.getLogger("dbbackup")
            exc_type, exc_value, tb = sys.exc_info()
            tb_str = "".join(traceback.format_tb(tb))
            msg = f"{exc_type.__name__}: {exc_value}\n{tb_str}"
            logger.exception(msg)
            raise
        finally:
            connection.close()

    return wrapper


def create_spooled_temporary_file(filepath=None, fileobj=None):
    """
    Create a spooled temporary file. if ``filepath`` or ``fileobj`` is
    defined its content will be copied into temporary file.

    :param filepath: Path of input file
    :type filepath: str

    :param fileobj: Input file object
    :type fileobj: file

    :returns: Spooled temporary file
    :rtype: :class:`tempfile.SpooledTemporaryFile`
    """
    spooled_file = tempfile.SpooledTemporaryFile(max_size=settings.TMP_FILE_MAX_SIZE, dir=settings.TMP_DIR)
    if filepath:
        fileobj = open(filepath, "r+b")  # noqa: SIM115
    if fileobj is not None:
        fileobj.seek(0)
        copyfileobj(fileobj, spooled_file, settings.TMP_FILE_READ_SIZE)
    return spooled_file


def encrypt_file(inputfile, filename):
    """
    Encrypt input file using GPG and remove .gpg extension to its name.

    :param inputfile: File to encrypt
    :type inputfile: ``file`` like object

    :param filename: File's name
    :type filename: ``str``

    :returns: Tuple with file and new file's name
    :rtype: :class:`tempfile.SpooledTemporaryFile`, ``str``
    """
    import gnupg

    tempdir = tempfile.mkdtemp(dir=settings.TMP_DIR)
    try:
        filename = f"{filename}.gpg"
        filepath = os.path.join(tempdir, filename)
        if "b" not in inputfile.mode:
            msg = "Input file must be opened in binary mode."
            raise ValueError(msg)
        try:
            inputfile.seek(0)
            always_trust = settings.GPG_ALWAYS_TRUST
            g = gnupg.GPG()
            result = g.encrypt_file(
                inputfile,
                output=filepath,
                recipients=settings.GPG_RECIPIENT,
                always_trust=always_trust,
            )
            inputfile.close()
            if not result:
                msg = f"Encryption failed; status: {result.status}"
                raise EncryptionError(msg)
            return create_spooled_temporary_file(filepath), filename
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
    finally:
        os.rmdir(tempdir)


def unencrypt_file(inputfile, filename, passphrase=None):
    """
    Unencrypt input file using GPG and remove .gpg extension to its name.

    :param inputfile: File to encrypt
    :type inputfile: ``file`` like object

    :param filename: File's name
    :type filename: ``str``

    :param passphrase: Passphrase of GPG key, if equivalent to False, it will
                       be asked to user. If user answer an empty pass, no
                       passphrase will be used.
    :type passphrase: ``str`` or ``None``

    :returns: Tuple with file and new file's name
    :rtype: :class:`tempfile.SpooledTemporaryFile`, ``str``
    """
    import gnupg

    def get_passphrase(passphrase=passphrase):
        return passphrase or getpass("Input Passphrase: ") or None

    temp_dir = tempfile.mkdtemp(dir=settings.TMP_DIR)
    try:
        new_basename = os.path.basename(filename).replace(".gpg", "")
        temp_filename = os.path.join(temp_dir, new_basename)
        try:
            inputfile.seek(0)
            g = gnupg.GPG()
            result = g.decrypt_file(
                fileobj_or_path=inputfile,
                passphrase=get_passphrase(),
                output=temp_filename,
            )
            if not result:
                msg = f"Decryption failed; status: {result.status}"
                raise DecryptionError(msg)
            outputfile = create_spooled_temporary_file(temp_filename)
        finally:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
    finally:
        os.rmdir(temp_dir)
    return outputfile, new_basename


def compress_file(inputfile, filename):
    """
    Compress input file using gzip and change its name.

    :param inputfile: File to compress
    :type inputfile: ``file`` like object

    :param filename: File's name
    :type filename: ``str``

    :returns: Tuple with compressed file and new file's name
    :rtype: :class:`tempfile.SpooledTemporaryFile`, ``str``
    """
    outputfile = create_spooled_temporary_file()
    new_filename = f"{filename}.gz"
    zipfile = gzip.GzipFile(filename=filename, fileobj=outputfile, mode="wb")
    try:
        inputfile.seek(0)
        copyfileobj(inputfile, zipfile, settings.TMP_FILE_READ_SIZE)
    finally:
        zipfile.close()
    return outputfile, new_filename


def uncompress_file(inputfile, filename):
    """
    Uncompress this file using gzip and change its name.

    :param inputfile: File to compress
    :type inputfile: ``file`` like object

    :param filename: File's name
    :type filename: ``str``

    :returns: Tuple with file and new file's name
    :rtype: :class:`tempfile.SpooledTemporaryFile`, ``str``
    """
    zipfile = gzip.GzipFile(fileobj=inputfile, mode="rb")
    try:
        inputfile.seek(0)
        outputfile = create_spooled_temporary_file(fileobj=zipfile)
    finally:
        zipfile.close()
    new_basename = os.path.basename(filename).replace(".gz", "")
    return outputfile, new_basename


def timestamp(value):
    """
    Return the timestamp of a datetime.datetime object.

    :param value: a datetime object
    :type value: datetime.datetime

    :return: the timestamp
    :rtype: str
    """
    value = value if timezone.is_naive(value) else timezone.localtime(value)
    return value.strftime(settings.DATE_FORMAT)


def filename_details(filepath):
    # TODO: What was this function made for ?
    return ""


PATTERN_MATCHNG = (
    ("%a", r"[A-Z][a-z]+"),
    ("%A", r"[A-Z][a-z]+"),
    ("%w", r"\d"),
    ("%d", r"\d{2}"),
    ("%b", r"[A-Z][a-z]+"),
    ("%B", r"[A-Z][a-z]+"),
    ("%m", r"\d{2}"),
    ("%y", r"\d{2}"),
    ("%Y", r"\d{4}"),
    ("%H", r"\d{2}"),
    ("%I", r"\d{2}"),
    # ('%p', r'(?AM|PM|am|pm)'),
    ("%M", r"\d{2}"),
    ("%S", r"\d{2}"),
    ("%f", r"\d{6}"),
    # ('%z', r'\+\d{4}'),
    # ('%Z', r'(?|UTC|EST|CST)'),
    ("%j", r"\d{3}"),
    ("%U", r"\d{2}"),
    ("%W", r"\d{2}"),
    # ('%c', r'[A-Z][a-z]+ [A-Z][a-z]{2} \d{2} \d{2}:\d{2}:\d{2} \d{4}'),
    # ('%x', r'd{2}/d{2}/d{4}'),
    # ('%X', r'd{2}:d{2}:d{2}'),
    # ('%%', r'%'),
)


def datefmt_to_regex(datefmt):
    """
    Convert a strftime format string to a regex.

    :param datefmt: strftime format string
    :type datefmt: ``str``

    :returns: Equivalent regex
    :rtype: ``re.compite``
    """
    new_string = datefmt
    for pat, reg in PATTERN_MATCHNG:
        new_string = new_string.replace(pat, reg)
    return re.compile(f"({new_string})")


def filename_to_datestring(filename, datefmt=None):
    """
    Return the date part of a file name.

    :param datefmt: strftime format string, ``settings.DATE_FORMAT`` is used
                    if is ``None``
    :type datefmt: ``str`` or ``None``

    :returns: Date part or nothing if not found
    :rtype: ``str`` or ``NoneType``
    """
    datefmt = datefmt or settings.DATE_FORMAT
    regex = datefmt_to_regex(datefmt)
    search = regex.search(filename)
    if search:
        return search.groups()[0]
    return None


def filename_to_date(filename, datefmt=None):
    """
    Return a datetime from a file name.

    :param datefmt: strftime format string, ``settings.DATE_FORMAT`` is used
                    if is ``None``
    :type datefmt: ``str`` or ``NoneType``

    :returns: Date guessed or nothing if no date found
    :rtype: ``datetime.datetime`` or ``NoneType``
    """
    datefmt = datefmt or settings.DATE_FORMAT
    datestring = filename_to_datestring(filename, datefmt)
    if datestring is not None:
        return datetime.strptime(datestring, datefmt)
    return None


def filename_generate(extension, database_name="", servername=None, content_type="db", wildcard=None):
    """
    Create a new backup filename.

    :param extension: Extension of backup file
    :type extension: ``str``

    :param database_name: If it is database backup specify its name
    :type database_name: ``str``

    :param servername: Specify server name or by default ``settings.DBBACKUP_HOSTNAME``
    :type servername: ``str``

    :param content_type: Content type to backup, ``'media'`` or ``'db'``
    :type content_type: ``str``

    :param wildcard: Replace datetime with this wilecard regex
    :type content_type: ``str``

    :returns: Computed file name
    :rtype: ``str`
    """
    if content_type == "db":
        if "/" in database_name:
            database_name = os.path.basename(database_name)
        if "." in database_name:
            database_name = database_name.split(".")[0]
        template = settings.FILENAME_TEMPLATE
    elif content_type == "media":
        template = settings.MEDIA_FILENAME_TEMPLATE
    else:
        template = settings.FILENAME_TEMPLATE

    params = {
        "servername": servername or settings.HOSTNAME,
        "datetime": wildcard or datetime.now().strftime(settings.DATE_FORMAT),
        "databasename": database_name,
        "extension": extension,
        "content_type": content_type,
    }
    if callable(template):
        filename = template(**params)
    else:
        filename = template.format(**params)
        filename = REG_FILENAME_CLEAN.sub("-", filename)
        filename = filename[1:] if filename.startswith("-") else filename
    return filename
