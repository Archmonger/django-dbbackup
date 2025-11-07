# Configuration

## General settings

### DBBACKUP_DATABASES

List of key entries for `settings.DATABASES` which shall be used to
connect and create database backups.

Default: `list(settings.DATABASES.keys())` (keys of all entries listed)

### DBBACKUP_TMP_DIR

Local directory used for creating temporary files (for example while streaming
command output before uploading to storage).

Default: `tempfile.gettempdir()`

### DBBACKUP_TMP_FILE_READ_SIZE

Read chunk size (in bytes) when streaming temporary files. Increase this if
you're working with very large backups and want fewer read system calls; decrease
for memory constrained environments.

Default: `1024 * 1000` (≈1 MB)

### DBBACKUP_TMP_FILE_MAX_SIZE

Maximum size in bytes for file handling in memory before a temporary
file is written in `DBBACKUP_TMP_DIR`.

Default: `10*1024*1024`

### DBBACKUP_CLEANUP_KEEP and DBBACKUP_CLEANUP_KEEP_MEDIA

Number of most recent backups to keep when you pass the `--clean <amount>`
option to `dbbackup` or `mediabackup`. Older files beyond this count are
deleted. `DBBACKUP_CLEANUP_KEEP_MEDIA` defaults to the same value unless set.

Default: `10`

### DBBACKUP_CLEANUP_KEEP_FILTER

Optional callable for custom retention logic run during cleanup. Receives the
filename of a candidate backup slated for deletion and returns `True` to keep
or `False` to delete. Combine this with `--clean` to implement e.g. “keep all
end of month backups”.

Default: `lambda filename: False`

### DBBACKUP_DATE_FORMAT

`strftime` format string used when expanding `{datetime}` in filename
templates. Must contain only alphanumeric characters plus `_ - %`.

Default: `'%Y-%m-%d-%H%M%S'`

### DBBACKUP_HOSTNAME

Used to identify a backup by a server name in the file name.

Default: `socket.gethostname()`

### DBBACKUP_FILENAME_TEMPLATE

Template used to construct database backup filenames. May be a format string
or a callable. Default: `'{databasename}-{servername}-{datetime}.{extension}'`.
If you supply a function it must accept the keyword arguments shown below and
return the complete filename string (without path).

```python
def backup_filename(databasename, servername, datetime, extension, content_type):
    pass

DBBACKUP_FILENAME_TEMPLATE = backup_filename
```

Use a custom function if you need hierarchical prefixes (e.g. `year/month/`),
or naming compatible with automatic life cycle / expiration rules of your
object storage provider. `{datetime}` is rendered using `DBBACKUP_DATE_FORMAT`.

Note on cleanup (--clean): the cleanup logic matches backup files to a
database using the `{databasename}` value (the database alias/key from
`settings.DATABASES` or `DBBACKUP_CONNECTORS`). If you rely on the
`--clean` option to remove older database backups, ensure your
`DBBACKUP_FILENAME_TEMPLATE` includes `{databasename}` so files can be
correctly identified and filtered for deletion. When backing up a single
database using the default `databasename` (often `default`) this may not be
necessary, but it is required when you manage more than one database or use
custom connector keys.

### DBBACKUP_MEDIA_FILENAME_TEMPLATE

Same as `DBBACKUP_FILENAME_TEMPLATE`, but used for media backups.

Default: `'{servername}-{datetime}.{extension}'`

### DBBACKUP_MEDIA_PATH

Filesystem path whose contents are archived by the `mediabackup` command. By
default this is `settings.MEDIA_ROOT`.

Default: `settings.MEDIA_ROOT`

## Encrypting your backups

Backups may contain personal or otherwise sensitive data. When storing them
outside trusted infrastructure you should encrypt them. Keep your private
keys secure and ensure you have tested decryption in a disaster scenario.

You can encrypt a backup with the `--encrypt` option. The backup is done
using GPG.

```bash
python manage.py dbbackup --encrypt
```

...or when restoring from an encrypted backup:

```bash
python manage.py dbrestore --decrypt
```

Requirements:

-   Install the python package python-gnupg: `pip install python-gnupg>=0.5.0`.
-   You need a GPG key. ([GPG manual](https://www.gnupg.org/gph/en/manual/c14.html))
-   Set the setting `DBBACKUP_GPG_RECIPIENT` to the name of the GPG key.

Note (Windows): The `gpg` executable must be installed and on your PATH for encryption/decryption. If it is absent, django-dbbackup still works; only encryption-related features are unavailable. The test suite will automatically skip encryption tests when `gpg` is not found.

### DBBACKUP_GPG_ALWAYS_TRUST

If GPG does not fully trust the public key, encryption can fail. Setting this
to `True` adds `--trust-model always` to bypass trust checks (only do this in
controlled environments).

### DBBACKUP_GPG_RECIPIENT

Recipient (key ID, fingerprint, or email) used for GPG encryption. Required
when using `--encrypt` and for automatic decryption with `--decrypt`.

### DBBACKUP_CONNECTORS

Optional per database override mapping similar to `DATABASES`. Lets you define
different credentials / hosts exclusively for backup / restore operations
(e.g. read from a replica). Keys correspond to database aliases.

See the [Databases](databases.md) section for details on how to configure
connectors.

Default: `{}`

### DBBACKUP_CONNECTOR_MAPPING

Map custom database engine names (e.g. from wrappers like `transaction_hooks`
or third party observability packages) to an existing DBBackup connector class path.
Useful when a third party backend subclasses a supported Django backend but
uses a different engine string.

See the [Databases](databases.md) section for details on how to configure the
connector mapping.

Default: `{}`

## Email configuration

### DBBACKUP_SEND_EMAIL

Controls whether django-dbbackup sends an error email when an uncaught
exception is raised.

Default: `True`

### DBBACKUP_SERVER_EMAIL

The email address that error messages come from, such as those sent to
`DBBACKUP_ADMINS`.

Default: `django.conf.settings.SERVER_EMAIL`

### DBBACKUP_ADMINS

A list of recipients that receive error emails when `DEBUG=False` and an
unhandled exception occurs in a DBBackup command. Follows Django's standard
`ADMINS` tuple-of-tuples structure: `(('Full Name', 'email@example.com'), ...)`.

Default: `django.conf.settings.ADMINS`

### DBBACKUP_EMAIL_SUBJECT_PREFIX

Subject-line prefix for email messages sent by DBBackup.

Default: `'[dbbackup] '`

## Database configuration

By default DBBackup uses values from `settings.DATABASES`. Use
`DBBACKUP_CONNECTORS` (documented above) for backup specific overrides. See
[Database settings](databases.md) for backend specific options.

## Storage configuration

You must configure a storage backend (`STORAGES['dbbackup']`) to persist
backups. See [Storage settings](storage.md) for supported options.
