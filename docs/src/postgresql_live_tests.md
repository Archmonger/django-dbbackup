# PostgreSQL Live Testing

This document describes the live PostgreSQL testing infrastructure added to django-dbbackup to complement the existing mocked unit tests.

## Overview

The PostgreSQL connectors (`PgDumpConnector`, `PgDumpBinaryConnector`, `PgDumpGisConnector`) were previously only tested with mocked commands. These live tests validate the connectors against a real PostgreSQL database to ensure end-to-end functionality.

## Test Scripts

### `scripts/postgres_live_test.py`

The main live testing script that creates temporary PostgreSQL databases and runs real backup/restore operations.

**Features:**
- Creates isolated test databases with unique names and users
- Runs Django migrations on the test database
- Creates test data and verifies backup/restore functionality
- Automatically cleans up test databases and users
- Provides verbose logging for debugging

**Usage:**
```bash
# Test a single connector
python scripts/postgres_live_test.py --connector PgDumpConnector --verbose

# Test a specific connector
python scripts/postgres_live_test.py --connector PgDumpBinaryConnector

# Test all connectors (but may have Django configuration conflicts)
python scripts/postgres_live_test.py --all --verbose
```

### `scripts/postgres_live_test_simple.py`

A wrapper script that runs each connector test in isolation to avoid Django configuration conflicts.

**Usage:**
```bash
# Test all connectors in isolation
python scripts/postgres_live_test_simple.py --all --verbose

# Test a single connector
python scripts/postgres_live_test_simple.py --connector PgDumpConnector --verbose
```

## Hatch Integration

The live tests are integrated with the hatch environment system:

```bash
# Run single connector test
hatch run functional:postgres-test

# Run all connectors in isolation (recommended)
hatch run functional:postgres-test-all

# Run single connector in isolation
hatch run functional:postgres-test-isolated
```

## Prerequisites

### PostgreSQL Service
The tests require a running PostgreSQL service with peer authentication configured for the `postgres` user.

**Check PostgreSQL status:**
```bash
sudo systemctl status postgresql
```

**Start PostgreSQL if needed:**
```bash
sudo systemctl start postgresql
```

### Required Tools
- `psql` - PostgreSQL client
- `pg_dump` - PostgreSQL dump utility  
- `pg_restore` - PostgreSQL restore utility
- `pg_isready` - PostgreSQL connection checker
- `sudo` access to run commands as `postgres` user

### Python Dependencies
The tests require `psycopg2-binary` which is included in the `functional` hatch environment.

## Test Process

Each test follows this pattern:

1. **Database Setup**
   - Check PostgreSQL server connectivity
   - Create unique test database name (e.g., `dbbackup_test_1755626977`)
   - Create test user with password
   - Create database owned by test user

2. **Django Configuration**
   - Configure Django to use the test PostgreSQL database
   - Set the specific connector to test
   - Configure file storage for backup files

3. **Test Data Creation**
   - Run Django migrations
   - Create test data (CharModel and TextModel instances)

4. **Backup Operation**
   - Run `python -m django dbbackup --noinput`
   - Verify backup file creation

5. **Data Clearing**
   - Delete all test data from database
   - Verify database is empty

6. **Restore Operation**
   - Run `python -m django dbrestore --noinput`
   - Verify restored data matches original

7. **Cleanup**
   - Drop test database
   - Drop test user
   - Remove temporary directories

## Connector-Specific Testing

### PgDumpConnector
- Uses `pg_dump` to create SQL text files
- Uses `psql` to restore from SQL files
- File extension: `.psql`

### PgDumpBinaryConnector
- Uses `pg_dump --format=custom` to create binary dumps
- Uses `pg_restore` to restore from binary files
- File extension: `.psql.bin`
- Supports parallel restoration

### PgDumpGisConnector
- Same as PgDumpConnector but with PostGIS support
- Runs `CREATE EXTENSION IF NOT EXISTS postgis;` before restore
- Requires `ADMIN_USER` setting for extension creation

## Integration with Existing Tests

The live tests complement but do not replace the existing mocked unit tests:

- **Unit Tests**: Fast, isolated, test command generation and error handling
- **Live Tests**: Slower, end-to-end, test actual database operations

Both test types are important:
- Unit tests catch regressions quickly in CI
- Live tests validate real-world functionality

## Troubleshooting

### Authentication Issues
If you see password prompts, ensure PostgreSQL is configured for peer authentication:

```bash
# Check PostgreSQL authentication config
sudo grep -i "local.*all.*postgres" /etc/postgresql/*/main/pg_hba.conf
```

Should show:
```
local   all             postgres                                peer
```

### Permission Issues
Ensure the test runner has sudo access to run commands as the `postgres` user:

```bash
# Test PostgreSQL access
sudo -u postgres psql -c "SELECT version();"
```

### Database Cleanup
If tests are interrupted, you may need to manually clean up test databases:

```bash
# List test databases
sudo -u postgres psql -l | grep dbbackup_test

# Drop test databases
sudo -u postgres dropdb dbbackup_test_XXXXXXXXXX

# Drop test users
sudo -u postgres psql -c "DROP USER IF EXISTS postgres_user;"
```

## Future Enhancements

Potential improvements to the live testing infrastructure:

1. **Docker Integration**: Use Docker containers for isolated PostgreSQL instances
2. **PostGIS Testing**: Add specific PostGIS extension tests
3. **Multiple PostgreSQL Versions**: Test against different PostgreSQL versions
4. **Performance Testing**: Add performance benchmarks for large databases
5. **Error Scenario Testing**: Test backup/restore failure scenarios
6. **Schema-specific Testing**: Test the `SCHEMAS` setting functionality

## Example Test Output

```
🐘 Starting PostgreSQL Live Tests for django-dbbackup
============================================================

📋 Testing PgDumpConnector...
[Live Test] Starting backup/restore test with PgDumpConnector
[PostgreSQL Test] Setting up test database...
[PostgreSQL Test] Checking PostgreSQL connection...
[PostgreSQL Test] PostgreSQL server is ready
[PostgreSQL Test] Creating test database: dbbackup_test_1755626913
[Live Test] Creating test data...
Operations to perform:
  Apply all migrations: testapp
Running migrations:
  Applying testapp.0001_initial... OK
  Applying testapp.0002_textmodel... OK
[Live Test] Created CharModel: CharModel object (1)
[Live Test] Created TextModel: TextModel object (1)
[Live Test] Running database backup...
INFO Backing Up Database: dbbackup_test_1755626913
INFO Writing file to default-pkrvmubgrv54qmi-2025-08-19-130833.psql
[Live Test] Clearing test data...
[Live Test] Test data cleared successfully
[Live Test] Running database restore...
INFO Finding latest backup
INFO Restoring backup for database 'default' and server 'None'
INFO Restoring: default-pkrvmubgrv54qmi-2025-08-19-130833.psql
INFO Restore tempfile created: 12.7 KiB
[Live Test] Found 1 CharModel objects
[Live Test] Found 1 TextModel objects
[Live Test] Test data verification passed
[Live Test] ✅ PgDumpConnector backup/restore test PASSED
[PostgreSQL Test] Cleaning up test database...

============================================================
📊 Test Summary:
  PgDumpConnector: ✅ PASSED

Results: 1/1 tests passed
```