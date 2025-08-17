#!/usr/bin/env python3
"""Debug script to test what happens when database.split(',') is called with empty string."""

# Test what happens when we split empty string
empty_database = ""
print("empty_database:", repr(empty_database))
print("empty_database.split(','):", empty_database.split(','))
print("bool(empty_database):", bool(empty_database))

# This reproduces the exact line in the current code
def _get_database_keys_current(database):
    return database.split(",") if database else ["fallback"]

def _get_database_keys_buggy(database): 
    # This would be the buggy implementation mentioned in the issue
    return database.split(",") if database else ["fallback"]

print("Current implementation with empty string:", _get_database_keys_current(""))
print("Current implementation with None:", _get_database_keys_current(None))

# Maybe the issue is that at some point the logic was different?
# Let me test what happens if we accidentally have the wrong logic
print("What if we check database.split(','):", bool("".split(",")))
print("''.split(','):", "".split(","))