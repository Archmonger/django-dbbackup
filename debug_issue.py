#!/usr/bin/env python3
"""Debug script to reproduce the DBBACKUP_DATABASES issue."""

import os
import sys
import django
from django.conf import settings

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
        # Configure DBBACKUP_DATABASES to use non-default database
        DBBACKUP_DATABASES=['secondary'],
    )

django.setup()

# Now test the behavior
from dbbackup.management.commands.dbbackup import Command as DbbackupCommand
from dbbackup import settings as dbbackup_settings

print("Django DATABASES keys:", list(settings.DATABASES.keys()))
print("DBBACKUP_DATABASES setting:", getattr(settings, 'DBBACKUP_DATABASES', 'NOT SET'))
print("dbbackup.settings.DATABASES:", dbbackup_settings.DATABASES)

# Test the command behavior
command = DbbackupCommand()

# Simulate no -d option provided (this is the bug scenario)
command.database = ""
print("command.database:", repr(command.database))
print("command._get_database_keys():", command._get_database_keys())

# This should use 'secondary' database according to DBBACKUP_DATABASES
# but the bug report says it uses 'default' instead