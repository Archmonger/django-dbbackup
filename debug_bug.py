#!/usr/bin/env python3
"""Test to reproduce the exact bug described in the issue."""

import os
import sys
import django
from django.conf import settings
from unittest.mock import patch

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='debug-secret-key',
        INSTALLED_APPS=[
            'dbbackup',
        ],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            },
            'secondary': {
                'ENGINE': 'django.db.backends.sqlite3', 
                'NAME': ':memory:',
            }
        },
        # This is the key: configure DBBACKUP_DATABASES to use non-default database
        DBBACKUP_DATABASES=['secondary'],
    )

django.setup()

# Now test what happens in a management command scenario
from django.core.management import call_command
from dbbackup.management.commands.dbbackup import Command as DbbackupCommand
from dbbackup import settings as dbbackup_settings

print("=== Settings ===")
print("Django DATABASES keys:", list(settings.DATABASES.keys()))
print("DBBACKUP_DATABASES setting:", getattr(settings, 'DBBACKUP_DATABASES', 'NOT SET'))
print("dbbackup.settings.DATABASES:", dbbackup_settings.DATABASES)

print("\n=== Test the command behavior directly ===")
command = DbbackupCommand()

# Test case 1: when database option is None (not provided)
print("Test case 1: database option is None")
options = {'database': None}
command.database = options.get("database") or ""
print("command.database:", repr(command.database))
print("command._get_database_keys():", command._get_database_keys())

# Test case 2: when database option is empty string  
print("\nTest case 2: database option is empty string")
options = {'database': ''}
command.database = options.get("database") or ""
print("command.database:", repr(command.database))
print("command._get_database_keys():", command._get_database_keys())

# Test case 3: when database option is provided
print("\nTest case 3: database option is provided")
options = {'database': 'default'}
command.database = options.get("database") or ""
print("command.database:", repr(command.database))
print("command._get_database_keys():", command._get_database_keys())

print("\n=== Test the potential bug scenario ===")
# This is what the bug report might be referring to - if the condition was wrong
def buggy_get_database_keys(self):
    # BUGGY: This would check if the split result is truthy, not if the original string is truthy
    db_keys = self.database.split(",")
    return db_keys if db_keys else dbbackup_settings.DATABASES

command.database = ""
print("Buggy implementation result:", buggy_get_database_keys(command))
print("Notice how buggy version returns [''] instead of", dbbackup_settings.DATABASES)