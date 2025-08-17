#!/usr/bin/env python3
"""
Test to simulate the exact bug described in the issue.
"""

print("=== Simulating the bug scenario ===")

# The bug is: "If a -d option is not given, this code will always evaluate to [''], 
# with the result that default is the database chosen."

# Current correct implementation:
def current_get_database_keys(database, fallback_databases):
    return database.split(",") if database else fallback_databases

# The buggy implementation that the issue might be referring to:
def buggy_get_database_keys(database, fallback_databases):
    # This is WRONG: checks the split result instead of the original string
    db_keys = database.split(",") 
    return db_keys if db_keys else fallback_databases

# Test scenario: no -d option provided
database = ""  # This is what gets set when no -d option is given
fallback_databases = ['secondary']  # This should be from DBBACKUP_DATABASES

print(f"Input database string: {repr(database)}")
print(f"Fallback databases (from DBBACKUP_DATABASES): {fallback_databases}")
print()

print("Current (correct) implementation:")
result = current_get_database_keys(database, fallback_databases)
print(f"Result: {result}")
print(f"Correctly uses fallback: {'✅' if result == fallback_databases else '❌'}")
print()

print("Buggy implementation (what the issue describes):")
result = buggy_get_database_keys(database, fallback_databases)
print(f"Result: {result}")
print(f"Incorrectly returns ['']: {'✅' if result == [''] else '❌'}")
print()

print("=== Why the bug happens ===")
print(f"''.split(',') = {repr(''.split(','))}")
print(f"bool(['']) = {bool([''])}")  # This is True!
print("So if the condition was 'if db_keys:' instead of 'if database:', it would be buggy")