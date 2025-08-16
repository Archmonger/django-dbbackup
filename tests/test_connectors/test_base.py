import os
from tempfile import SpooledTemporaryFile

from django.test import TestCase

from dbbackup.db import exceptions
from dbbackup.db.base import BaseCommandDBConnector, BaseDBConnector, get_connector


class GetConnectorTest(TestCase):
    def test_get_connector(self):
        connector = get_connector()
        self.assertIsInstance(connector, BaseDBConnector)


class BaseDBConnectorTest(TestCase):
    def test_init(self):
        BaseDBConnector()

    def test_settings(self):
        connector = BaseDBConnector()
        connector.settings

    def test_generate_filename(self):
        connector = BaseDBConnector()
        connector.generate_filename()


class BaseCommandDBConnectorTest(TestCase):
    def test_run_command(self):
        connector = BaseCommandDBConnector()
        stdout, stderr = connector.run_command("echo 123")
        self.assertEqual(stdout.read(), b"123\n")
        self.assertEqual(stderr.read(), b"")

    def test_run_command_error(self):
        connector = BaseCommandDBConnector()
        with self.assertRaises(exceptions.CommandConnectorError):
            connector.run_command("echa 123")

    def test_run_command_stdin(self):
        connector = BaseCommandDBConnector()
        stdin = SpooledTemporaryFile()
        stdin.write(b"foo")
        stdin.seek(0)
        # Run
        stdout, stderr = connector.run_command("cat", stdin=stdin)
        self.assertEqual(stdout.read(), b"foo")
        self.assertFalse(stderr.read())

    def test_run_command_with_env(self):
        connector = BaseCommandDBConnector()
        # Empty env
        stdout, stderr = connector.run_command("env")
        self.assertTrue(stdout.read())
        # env from self.env
        connector.env = {"foo": "bar"}
        stdout, stderr = connector.run_command("env")
        self.assertIn(b"foo=bar\n", stdout.read())
        # method override global env
        stdout, stderr = connector.run_command("env", env={"foo": "ham"})
        self.assertIn(b"foo=ham\n", stdout.read())
        # get a var from parent env
        os.environ["bar"] = "foo"
        stdout, stderr = connector.run_command("env")
        self.assertIn(b"bar=foo\n", stdout.read())
        # Conf overrides parendt env
        connector.env = {"bar": "bar"}
        stdout, stderr = connector.run_command("env")
        self.assertIn(b"bar=bar\n", stdout.read())
        # method overrides all
        stdout, stderr = connector.run_command("env", env={"bar": "ham"})
        self.assertIn(b"bar=ham\n", stdout.read())

    def test_run_command_with_parent_env(self):
        connector = BaseCommandDBConnector(use_parent_env=False)
        # Empty env
        stdout, stderr = connector.run_command("env")
        self.assertFalse(stdout.read())
        # env from self.env
        connector.env = {"foo": "bar"}
        stdout, stderr = connector.run_command("env")
        self.assertEqual(stdout.read(), b"foo=bar\n")
        # method override global env
        stdout, stderr = connector.run_command("env", env={"foo": "ham"})
        self.assertEqual(stdout.read(), b"foo=ham\n")
        # no var from parent env
        os.environ["bar"] = "foo"
        stdout, stderr = connector.run_command("env")
        self.assertNotIn(b"bar=foo\n", stdout.read())
