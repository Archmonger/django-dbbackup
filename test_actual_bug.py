#!/usr/bin/env python3
"""
Create a realistic test to see if the issue actually exists.
"""

import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
from django.conf import settings

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
        # This is the key setting - we want 'secondary' to be backed up, not 'default'
        DBBACKUP_DATABASES=['secondary'],
        STORAGES={
            'dbbackup': {
                'BACKEND': 'django.core.files.storage.FileSystemStorage',
                'OPTIONS': {
                    'location': tempfile.gettempdir(),
                },
            },
        },
    )

django.setup()

from dbbackup.management.commands.dbbackup import Command as DbbackupCommand
from dbbackup.db.base import get_connector
from dbbackup.storage import get_storage

print("=== Test actual command execution ===")

# Mock the actual backup creation to avoid side effects
with patch('dbbackup.db.sqlite.SqliteConnector.create_dump') as mock_create_dump:
    mock_create_dump.return_value = MagicMock()
        
        # Create command and simulate calling it without -d option
        command = DbbackupCommand()
        
        # Simulate command line parsing (no -d option provided)
        options = {
            'verbosity': 1,
            'quiet': False, 
            'clean': False,
            'database': None,  # This is the key - no -d option means None
            'servername': None,
            'compress': False,
            'encrypt': False,
            'output_filename': None,
            'output_path': None,
            'exclude_tables': None,
            'schema': [],
        }
        
        print("Options passed to command:", options)
        
        # Track which databases get processed
        processed_databases = []
        original_save_new_backup = command._save_new_backup
        
        def track_backup(database):
            processed_databases.append(database['NAME'])
            print(f"Processing backup for database: {database['NAME']}")
            # Don't actually run the backup
            return None
            
        command._save_new_backup = track_backup
        
        try:
            command.handle(**options)
            print(f"Databases that were backed up: {processed_databases}")
            
            # The bug would be if 'default' database gets backed up instead of 'secondary'
            if 'default' in processed_databases and 'secondary' not in processed_databases:
                print("❌ BUG CONFIRMED: 'default' database was backed up instead of 'secondary'")
            elif 'secondary' in processed_databases and 'default' not in processed_databases:
                print("✅ WORKING CORRECTLY: 'secondary' database was backed up as expected")
            else:
                print(f"⚠️  UNEXPECTED: Both or neither databases processed: {processed_databases}")
                
        except Exception as e:
            print(f"Error during command execution: {e}")
            import traceback
            traceback.print_exc()