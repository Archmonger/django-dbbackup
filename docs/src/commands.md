# Commands

The primary usage of DBBackup is with command line tools. By default, commands will create backups and upload to your defined storage or download and restore the latest backup.

Arguments can be passed to commands to compress/uncompress and encrypt/decrypt.

## dbbackup

Backup of database.

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

Restore a database.

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

Backup media files, gather all in a tarball and encrypt or compress.

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

Restore media files, extract files from archive and put into media storage.

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

This command helps to list backups filtered by type (`'media'` or `'db'`), by compression or encryption.

For detailed help information, run:

```bash
python manage.py listbackups --help
```
