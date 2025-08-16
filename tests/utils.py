import contextlib
import os
import subprocess

from django.conf import settings
from django.core.files import File
from django.core.files.storage import Storage
from django.utils import timezone

from dbbackup.db.base import get_connector

BASE_FILE = os.path.join(settings.BLOB_DIR, "test.txt")
ENCRYPTED_FILE = os.path.join(settings.BLOB_DIR, "test.txt.gpg")
COMPRESSED_FILE = os.path.join(settings.BLOB_DIR, "test.txt.gz")
TARED_FILE = os.path.join(settings.BLOB_DIR, "test.txt.tar")
ENCRYPTED_COMPRESSED_FILE = os.path.join(settings.BLOB_DIR, "test.txt.gz.gpg")
TEST_DATABASE = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": "/tmp/foo.db",
    "USER": "foo",
    "PASSWORD": "bar",
    "HOST": "foo",
    "PORT": 122,
}
TEST_MONGODB = {
    "ENGINE": "django_mongodb_engine",
    "NAME": "mongo_test",
    "USER": "foo",
    "PASSWORD": "bar",
    "HOST": "foo",
    "PORT": 122,
}
TEST_DATABASE = settings.DATABASES["default"]

GPG_PRIVATE_PATH = os.path.join(settings.BLOB_DIR, "gpg/secring.gpg")
GPG_PUBLIC_PATH = os.path.join(settings.BLOB_DIR, "gpg/pubring.gpg")
GPG_FINGERPRINT = "7438 8D4E 02AF C011 4E2F  1E79 F7D1 BBF0 1F63 FDE9"
DEV_NULL = open(os.devnull, "w")


class handled_files(dict):
    """
    Dict for gather information about fake storage and clean between tests.
    You should use the constant instance ``HANDLED_FILES`` and clean it
    before tests.
    """

    def __init__(self):
        super().__init__()
        self.clean()

    def clean(self):
        self["written_files"] = []
        self["deleted_files"] = []


HANDLED_FILES = handled_files()


class FakeStorage(Storage):
    name = "FakeStorage"

    def exists(self, name):
        return name in HANDLED_FILES["written_files"]

    def get_available_name(self, name, max_length=None):
        return name[:max_length]

    def get_valid_name(self, name):
        return name

    def listdir(self, path):
        return ([], [f[0] for f in HANDLED_FILES["written_files"]])

    def accessed_time(self, name):
        return timezone.now()

    created_time = modified_time = accessed_time

    def _open(self, name, mode="rb"):
        file_ = [f[1] for f in HANDLED_FILES["written_files"] if f[0] == name][0]
        file_.seek(0)
        return file_

    def _save(self, name, content):
        HANDLED_FILES["written_files"].append((name, File(content)))
        return name

    def delete(self, name):
        HANDLED_FILES["deleted_files"].append(name)


def clean_gpg_keys():
    with contextlib.suppress(Exception):
        cmd = "gpg --batch --yes --delete-key '%s'" % GPG_FINGERPRINT
        subprocess.call(cmd, stdout=DEV_NULL, stderr=DEV_NULL)
    with contextlib.suppress(Exception):
        cmd = "gpg --batch --yes --delete-secrect-key '%s'" % GPG_FINGERPRINT
        subprocess.call(cmd, stdout=DEV_NULL, stderr=DEV_NULL)


def add_private_gpg():
    cmd = f"gpg --import {GPG_PRIVATE_PATH}".split()
    subprocess.call(cmd, stdout=DEV_NULL, stderr=DEV_NULL)


def add_public_gpg():
    cmd = f"gpg --import {GPG_PUBLIC_PATH}".split()
    subprocess.call(cmd, stdout=DEV_NULL, stderr=DEV_NULL)


def callable_for_filename_template(datetime, **kwargs):
    return f"{datetime}_foo"


def get_dump(database=TEST_DATABASE):
    return get_connector().create_dump()


def get_dump_name(database=None):
    database = database or TEST_DATABASE
    return get_connector().generate_filename()
