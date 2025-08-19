# Commands

DBBackup exposes Django management commands for creating and restoring
database and media backups. Without extra arguments `dbbackup` and
`mediabackup` create a backup and upload it to the configured
`STORAGES['dbbackup']` backend; `dbrestore` / `mediarestore` download and
restore the most recent matching backup.

Use `python manage.py <command> --help` for full option details.

## dbbackup

Create a database backup (optionally compressed/encrypted) and upload it.

```bash
$ ./manage.py dbbackup
Backing Up Database: tmp.x0kN9sYSqk
Backup size: 3.3 KiB
Writing file to tmp-zuluvm-2016-07-29-100954.dump
```

For detailed help information, run:

```bash
python manage.py dbbackup --help
```

## dbrestore

Download the latest database backup (or a specified one) then restore it.

```bash
$ ./manage.py dbrestore
Restoring backup for database: tmp.x0kN9sYSqk
Finding latest backup
Restoring: tmp-zuluvm-2016-07-29-100954.dump
Restore tempfile created: 3.3 KiB
```

For detailed help information, run:

```bash
python manage.py dbrestore --help
```

## mediabackup

Create an archive (tar) of media files, optionally compress/encrypt, and upload
it to backup storage.

```bash
$ ./manage.py mediabackup
Backup size: 10.0 KiB
Writing file to zuluvm-2016-07-04-081612.tar
```

For detailed help information, run:

```bash
python manage.py mediabackup --help
```

## mediarestore

Restore media files: extract files from the archive and put them into media storage.

```bash
$ ./manage.py mediarestore
Restoring backup for media files
Finding latest backup
Reading file zuluvm-2016-07-04-082551.tar
Restoring: zuluvm-2016-07-04-082551.tar
Backup size: 10.0 KiB
Are you sure you want to continue? [Y/n]
2 file(s) restored
```

For detailed help information, run:

```bash
python manage.py mediarestore --help
```

## listbackups

This command lists backups filtered by type (`'media'` or `'db'`), compression, or encryption.

For detailed help information, run:

```bash
python manage.py listbackups --help
```
