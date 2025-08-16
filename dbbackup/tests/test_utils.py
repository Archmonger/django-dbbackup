import os
import tempfile
from datetime import datetime
from io import StringIO
from unittest.mock import patch

import django
import pytz
from django.core import mail
from django.test import TestCase

from dbbackup import settings, utils
from dbbackup.tests.utils import (
    COMPRESSED_FILE,
    ENCRYPTED_FILE,
    add_private_gpg,
    add_public_gpg,
    callable_for_filename_template,
    clean_gpg_keys,
)


class Bytes_To_StrTest(TestCase):
    def test_get_gb(self):
        value = utils.bytes_to_str(byteVal=2**31)
        self.assertEqual(value, "2.0 GiB")

    def test_0_decimal(self):
        value = utils.bytes_to_str(byteVal=1.01, decimals=0)
        self.assertEqual(value, "1 B")

    def test_2_decimal(self):
        value = utils.bytes_to_str(byteVal=1.01, decimals=2)
        self.assertEqual(value, "1.01 B")


class Handle_SizeTest(TestCase):
    def test_func(self):
        filehandle = StringIO("Test string")
        value = utils.handle_size(filehandle=filehandle)
        self.assertEqual(value, "11.0 B")


class MailAdminsTest(TestCase):
    def test_func(self):
        subject = "foo subject"
        msg = "bar message"

        utils.mail_admins(subject, msg)
        self.assertEqual(len(mail.outbox), 1)

        sent_mail = mail.outbox[0]
        expected_subject = f"{settings.EMAIL_SUBJECT_PREFIX}{subject}"
        expected_to = settings.ADMINS[0][1]
        expected_from = settings.SERVER_EMAIL

        self.assertEqual(sent_mail.subject, expected_subject)
        self.assertEqual(sent_mail.body, msg)
        self.assertEqual(sent_mail.to[0], expected_to)
        self.assertEqual(sent_mail.from_email, expected_from)

    @patch("dbbackup.settings.ADMINS", None)
    def test_no_admin(self):
        subject = "foo subject"
        msg = "bar message"
        self.assertIsNone(utils.mail_admins(subject, msg))
        self.assertEqual(len(mail.outbox), 0)


class Email_Uncaught_ExceptionTest(TestCase):
    def test_success(self):
        def func():
            pass

        utils.email_uncaught_exception(func)
        self.assertEqual(len(mail.outbox), 0)

    @patch("dbbackup.settings.SEND_EMAIL", False)
    def test_raise_error_without_mail(self):
        def func():
            raise Exception("Foo")

        with self.assertRaises(Exception):
            utils.email_uncaught_exception(func)()
        self.assertEqual(len(mail.outbox), 0)

    @patch("dbbackup.settings.SEND_EMAIL", True)
    @patch("dbbackup.settings.FAILURE_RECIPIENTS", ["foo@bar"])
    def test_raise_with_mail(self):
        def func():
            raise Exception("Foo")

        with self.assertRaises(Exception):
            utils.email_uncaught_exception(func)()
        self.assertEqual(len(mail.outbox), 1)
        error_mail = mail.outbox[0]
        self.assertEqual(["foo@bar"], error_mail.to)
        self.assertIn('Exception("Foo")', error_mail.subject)
        if django.VERSION >= (1, 7):
            self.assertIn('Exception("Foo")', error_mail.body)


class Encrypt_FileTest(TestCase):
    def setUp(self):
        self.path = tempfile.mktemp()
        with open(self.path, "a") as fd:
            fd.write("foo")
        add_public_gpg()

    def tearDown(self):
        os.remove(self.path)
        clean_gpg_keys()

    def test_func(self, *args):
        with open(self.path, mode="rb") as fd:
            encrypted_file, filename = utils.encrypt_file(
                inputfile=fd, filename="foo.txt"
            )
        encrypted_file.seek(0)
        self.assertTrue(encrypted_file.read())


class Unencrypt_FileTest(TestCase):
    def setUp(self):
        add_private_gpg()

    def tearDown(self):
        clean_gpg_keys()

    @patch("dbbackup.utils.input", return_value=None)
    @patch("dbbackup.utils.getpass", return_value=None)
    def test_unencrypt(self, *args):
        inputfile = open(ENCRYPTED_FILE, "r+b")
        uncryptfile, filename = utils.unencrypt_file(inputfile, "foofile.gpg")
        uncryptfile.seek(0)
        self.assertEqual(b"foo\n", uncryptfile.read())


class Compress_FileTest(TestCase):
    def setUp(self):
        self.path = tempfile.mktemp()
        with open(self.path, "a+b") as fd:
            fd.write(b"foo")

    def tearDown(self):
        os.remove(self.path)

    def test_func(self, *args):
        with open(self.path, mode="rb") as fd:
            compressed_file, filename = utils.encrypt_file(
                inputfile=fd, filename="foo.txt"
            )


class Uncompress_FileTest(TestCase):
    def test_func(self):
        inputfile = open(COMPRESSED_FILE, "rb")
        fd, filename = utils.uncompress_file(inputfile, "foo.gz")
        fd.seek(0)
        self.assertEqual(fd.read(), b"foo\n")


class Create_Spooled_Temporary_FileTest(TestCase):
    def setUp(self):
        self.path = tempfile.mktemp()
        with open(self.path, "a") as fd:
            fd.write("foo")

    def tearDown(self):
        os.remove(self.path)

    def test_func(self, *args):
        utils.create_spooled_temporary_file(filepath=self.path)


class TimestampTest(TestCase):
    def test_naive_value(self):
        with self.settings(USE_TZ=False):
            timestamp = utils.timestamp(datetime(2015, 8, 15, 8, 15, 12, 0))
            self.assertEqual(timestamp, "2015-08-15-081512")

    def test_aware_value(self):
        with self.settings(USE_TZ=True) and self.settings(TIME_ZONE="Europe/Rome"):
            timestamp = utils.timestamp(
                datetime(2015, 8, 15, 8, 15, 12, 0, tzinfo=pytz.utc)
            )
            self.assertEqual(timestamp, "2015-08-15-101512")


class Datefmt_To_Regex(TestCase):
    def test_patterns(self):
        now = datetime.now()
        for datefmt, regex in utils.PATTERN_MATCHNG:
            date_string = datetime.strftime(now, datefmt)
            regex = utils.datefmt_to_regex(datefmt)
            match = regex.match(date_string)
            self.assertTrue(match)
            self.assertEqual(match.groups()[0], date_string)

    def test_complex_pattern(self):
        now = datetime.now()
        datefmt = "Foo%a_%A-%w-%d-%b-%B_%m_%y_%Y-%H-%I-%M_%S_%f_%j-%U-%W-Bar"
        date_string = datetime.strftime(now, datefmt)
        regex = utils.datefmt_to_regex(datefmt)
        self.assertTrue(regex.pattern.startswith("(Foo"))
        self.assertTrue(regex.pattern.endswith("Bar)"))
        match = regex.match(date_string)
        self.assertTrue(match)
        self.assertEqual(match.groups()[0], date_string)


class Filename_To_DatestringTest(TestCase):
    def test_func(self):
        now = datetime.now()
        datefmt = settings.DATE_FORMAT
        filename = f"{datetime.strftime(now, datefmt)}-foo.gz.gpg"
        datestring = utils.filename_to_datestring(filename, datefmt)
        self.assertIn(datestring, filename)

    def test_generated_filename(self):
        filename = utils.filename_generate("bak", "default")
        datestring = utils.filename_to_datestring(filename)
        self.assertIn(datestring, filename)


class Filename_To_DateTest(TestCase):
    def test_func(self):
        now = datetime.now()
        datefmt = settings.DATE_FORMAT
        filename = f"{datetime.strftime(now, datefmt)}-foo.gz.gpg"
        date = utils.filename_to_date(filename, datefmt)
        self.assertEqual(date.timetuple()[:5], now.timetuple()[:5])

    def test_generated_filename(self):
        filename = utils.filename_generate("bak", "default")
        utils.filename_to_date(filename)


@patch("dbbackup.settings.HOSTNAME", "test")
class Filename_GenerateTest(TestCase):
    @patch(
        "dbbackup.settings.FILENAME_TEMPLATE",
        "---{databasename}--{servername}-{datetime}.{extension}",
    )
    def test_func(self, *args):
        extension = "foo"
        generated_name = utils.filename_generate(extension)
        self.assertTrue("--" not in generated_name)
        self.assertFalse(generated_name.startswith("-"))

    def test_db(self, *args):
        extension = "foo"
        generated_name = utils.filename_generate(extension)
        self.assertTrue(generated_name.startswith(settings.HOSTNAME))
        self.assertTrue(generated_name.endswith(extension))

    def test_media(self, *args):
        extension = "foo"
        generated_name = utils.filename_generate(extension, content_type="media")
        self.assertTrue(generated_name.startswith(settings.HOSTNAME))
        self.assertTrue(generated_name.endswith(extension))

    @patch("django.utils.timezone.settings.USE_TZ", True)
    def test_tz_true(self):
        filename = utils.filename_generate("bak", "default")
        datestring = utils.filename_to_datestring(filename)
        self.assertIn(datestring, filename)

    @patch("dbbackup.settings.FILENAME_TEMPLATE", callable_for_filename_template)
    def test_template_is_callable(self, *args):
        extension = "foo"
        generated_name = utils.filename_generate(extension)
        self.assertTrue(generated_name.endswith("foo"))


class QuoteCommandArg(TestCase):
    def test_arg_with_space(self):
        assert utils.get_escaped_command_arg("foo bar") == "'foo bar'"
