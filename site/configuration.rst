Configuration
=============

General settings
----------------

DBBACKUP_DATABASES
~~~~~~~~~~~~~~~~~~

List of key entries for ``settings.DATABASES`` which shall be used to
connect and create database backups.

Default: ``list(settings.DATABASES.keys())`` (keys of all entries listed)

DBBACKUP_TMP_DIR
~~~~~~~~~~~~~~~~

Directory to be used in local filesystem for temporary files.

Default: ``tempfile.gettempdir()``

DBBACKUP_TMP_FILE_MAX_SIZE
~~~~~~~~~~~~~~~~~~~~~~~~~~

Maximum size in bytes for file handling in memory before a temporary
file is written in ``DBBACKUP_TMP_DIR``.

Default: ``10*1024*1024``


DBBACKUP_CLEANUP_KEEP and DBBACKUP_CLEANUP_KEEP_MEDIA
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When issuing ``dbbackup`` and ``mediabackup`` with ``--clean <amount>`` option,
the backup keeps this amount of most recent files. Older files are removed. 

Default: ``10`` (backups)


DBBACKUP_CLEANUP_KEEP_FILTER
~~~~~~~~~~~~~~~~~~~~~~~

A callable that takes a filename (of an old backup, to be cleaned) and returns
a boolean indicating whether the backup should be kept (``True``) or deleted
(``False``).

Default: ``lambda filename: False``

This can be used to keep monthly backups, for example.


DBBACKUP_DATE_FORMAT
~~~~~~~~~~~~~~~~~~~~

Date format to use for naming files. It must contain only alphanumerical
characters, ``'_'``, ``'-'`` or ``'%'``.

Default: ``'%Y-%m-%d-%H%M%S'``


DBBACKUP_HOSTNAME
~~~~~~~~~~~~~~~~~

Used to identify a backup by a server name in the file name.

Default: ``socket.gethostname()``


DBBACKUP_FILENAME_TEMPLATE
~~~~~~~~~~~~~~~~~~~~~~~~~~

The template to use when generating the backup filename. By default this is
``'{databasename}-{servername}-{datetime}.{extension}'``. This setting can
also be made a function which takes the following keyword arguments:

::

    def backup_filename(databasename, servername, datetime, extension, content_type):
        pass

    DBBACKUP_FILENAME_TEMPLATE = backup_filename

This allows you to modify the entire format of the filename, for example, if
you want to take advantage of Amazon S3's automatic expiry feature, you need
to prefix your backups differently based on when you want them to expire.

``{datetime}`` is rendered with ``DBBACKUP_DATE_FORMAT``.


DBBACKUP_MEDIA_FILENAME_TEMPLATE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Same as ``DBBACKUP_FILENAME_TEMPLATE`` but for media files backups.


Encrypting your backups
-----------------------

Considering that you might be putting secure data on external servers and
perhaps untrusted servers where it gets forgotten over time, it's always a
good idea to encrypt backups.

Just remember to keep the encryption keys safe, too!


PGP
~~~

You can encrypt a backup with the ``--encrypt`` option. The backup is done
using GPG. ::

    python manage.py dbbackup --encrypt

...or when restoring from an encrypted backup: ::

    python manage.py dbrestore --decrypt


Requirements:

-  Install the python package python-gnupg:
   ``pip install python-gnupg>=0.5.0``.
-  You need a GPG key. (`GPG manual`_)
-  Set the setting ``DBBACKUP_GPG_RECIPIENT`` to the name of the GPG key.

.. _`GPG manual`: https://www.gnupg.org/gph/en/manual/c14.html


DBBACKUP_GPG_ALWAYS_TRUST
~~~~~~~~~~~~~~~~~~~~~~~~~

The encryption of the backup file fails if GPG does not trust the public
encryption key. The solution is to set the option 'trust-model' to 'always'.
By default this value is ``False``. Set this to ``True`` to enable this option.


DBBACKUP_GPG_RECIPIENT
~~~~~~~~~~~~~~~~~~~~~~

The name of the key that is used for encryption. This setting is only used
when making a backup with the ``--encrypt`` or ``--decrypt`` option.


Email configuration
-------------------

DBBACKUP_SEND_EMAIL
~~~~~~~~~~~~~~~~~~~

Controls whether or not django-dbbackup sends an error email when an uncaught
exception is received.

Default: ``True``


DBBACKUP_SERVER_EMAIL
~~~~~~~~~~~~~~~~~~~~~

The email address that error messages come from, such as those sent to
``DBBACKUP_ADMINS``.

Default: ``django.conf.settings.SERVER_EMAIL``


DBBACKUP_ADMINS
~~~~~~~~~~~~~~~

A list of all the people who get code error notifications. When ``DEBUG=False``
and an operation raises an exception, DBBackup will email these people with the
full exception information. This should be a tuple of (Full name,
email address).

Default: ``django.conf.settings.ADMINS``

.. warning::

    ``DBBACKUP_FAILURE_RECIPIENTS`` was used before and is now deprecated



DBBACKUP_EMAIL_SUBJECT_PREFIX
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Subject-line prefix for email messages sent by DBBackup.

Default: ``'[dbbackup] '``


Database configuration
----------------------

By default, DBBackup uses parameters from ``settings.DATABASES`` but you can
make an independent configuration, see `Database settings`_


Storage configuration
---------------------

You have to use a storage for your backups, see `Storage settings`_ for more.

.. _`Database settings`: databases.html
.. _`Storage settings`: storage.html
