Storage settings
================

One of the most helpful features of django-dbbackup is the ability to store
and retrieve backups from a local or a remote storage. This functionality is
mainly based on Django Storage API and extends its possibilities.

You can choose your backup storage backend by setting ``settings.STORAGES['dbbackup']``,
it must be the full path of a storage class. For example:
``django.core.files.storage.FileSystemStorage`` to use file system storage. 
Below, we'll list some of the available solutions and their options.


The storage's option are gathered in ``settings.STORAGES['dbbackup']['OPTIONS']`` which
is a dictionary of keywords representing how to configure it.

    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {
            ...your_options_here
            },
        },
        "staticfiles": {
            ...
        },
    }


.. warning::

    Do not configure backup storage with the same configuration as your media
    files as you'll risk sharing backups inside public directories.

By default DBBackup uses the `built-in file system storage`_ to manage files on
a local directory. Feel free to use any Django storage, you can find a variety
of them at `Django Packages`_.

.. _`built-in file system storage`:
    https://docs.djangoproject.com/en/stable/ref/files/storage/#the-filesystemstorage-class
.. _`Django Packages`: https://djangopackages.org/grids/g/storage-backends/

.. note::

    Storing backups to local disk may also be useful for Dropbox if you
    already have the official Dropbox client installed on your system.

File system storage
-------------------

Setup
~~~~~

To store your backups on the local file system, simply setup the required
settings below. ::

    STORAGES = {
        "dbbackup": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {
                "location": "/my/backup/dir/",
            },
        },
    }

Available settings
~~~~~~~~~~~~~~~~~~

**location**

Absolute path to the directory that will hold the files.

**file_permissions_mode**

The file system permissions that the file will receive when it is saved.

**directory_permissions_mode**

The file system permissions that the directory will receive when it is saved.

See `FileSystemStorage's documentation`_ for a full list of available settings.

.. _`FileSystemStorage's documentation`:
    https://docs.djangoproject.com/en/stable/ref/files/storage/#the-filesystemstorage-class

Google cloud storage
--------------------
Our backend for Google cloud storage uses django-storages.

Setup
~~~~~

In order to backup to Google cloud storage, you'll first need to create an account at google. Once that is complete, you can follow the required setup below. ::

    pip install django-storages[google]

Add the following to your project's settings. Strictly speaking only `bucket_name` is required, but we'd recommend to add the other two as well. You can also find more settings in the readme for `django-storages`_ ::

    STORAGES = {
        "dbbackup": {
            "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
            "OPTIONS": {
                "bucket_name": "your_bucket_name",
                "project_id": "your_project_id",
                "blob_chunk_size": 1024 * 1024,
            },
        },
    }

.. _`django-storages`: https://django-storages.readthedocs.io/en/latest/backends/gcloud.html

Amazon S3
---------

Our S3 backend uses Django Storages which uses `boto3`_.

.. _`boto3`: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html

Setup
~~~~~

In order to backup to Amazon S3, you'll first need to create an Amazon
Webservices Account and setup your Amazon S3 bucket. Once that is
complete, you can follow the required setup below. ::

    pip install django-storages[boto3]

Add the following to your project's settings: ::

    STORAGES = {
        "dbbackup": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "access_key": "my_id",
                "secret_key": "my_secret",
                "bucket_name": "my_bucket_name",
                "default_acl": "private",
            },
        }
    }

Available settings
~~~~~~~~~~~~~~~~~~

.. note::

    See the `Django Storage S3 storage official documentation`_ for all options.

    The options listed here are a selection of dictionary keys returned by
    ``get_default_settings`` in django-storages' `storages/backends/s3boto3.py`_,
    which allows us to write nicer code compared to using the ``AWS_`` prefixed
    settings.

.. _`Django Storage S3 storage official documentation`:
    https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html
.. _`storages/backends/s3boto3.py`:
    https://github.com/jschneier/django-storages/blob/master/storages/backends/s3boto3.py#L293-L324

**access_key** - Required

Your AWS access key as string. This can be found on your `Amazon Account
Security Credentials page`_.

.. _`Amazon Account Security Credentials page`:
    https://console.aws.amazon.com/iam/home#security_credential

**secret_key** - Required

Your Amazon Web Services secret access key, as a string.

**bucket_name** - Required

Your Amazon Web Services storage bucket name, as a string. This directory must
exist before attempting to create your first backup.

**region_name** - Optional

Specify the Amazon region, e.g. ``'us-east-1'``.

**endpoint_url** - Optional

Set this to fully override the endpoint, e.g. to use an alternative S3 service,
which is compatible with AWS S3.  The value must contain the protocol, e.g.
``'https://compatible-s3-service.example.com'``.

If setting this, it is mandatory to also configure **region_name**.

**default_acl** - Required

This setting can either be ``'private'`` or ``'public'``. Since you want your
backups to be secure you'll want to set ``'default_acl'`` to ``'private'``.

*NOTE: This value will be removed in a future version of django-storages.*
See their `CHANGELOG`_ for details.

**location** - Optional

If you want to store your backups inside a particular folder in your bucket you need to specify the ``'location'``.
The folder can be specified as ``'folder_name/'``.
You can specify a longer path with ``'location': 'root_folder/sub_folder/sub_sub_folder/'``.

.. _`CHANGELOG`: https://github.com/jschneier/django-storages/blob/master/CHANGELOG.rst

Dropbox
-------

In order to backup to Dropbox, you'll first need to create a Dropbox account
and set it up to communicate with the Django-DBBackup application. Don't
worry, all instructions are below.

Setup your Dropbox account
~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Login to Dropbox and navigate to Developers » MyApps.
   https://www.dropbox.com/developers/apps

2. Click the button to create a new app and name it whatever you like.
   As an example, I named mine 'Website Backups'.

3. After your app is created, note the options button and more
   importantly the 'App Key' and 'App Secret' values inside. You'll need
   those later.

Setup your Django project
~~~~~~~~~~~~~~~~~~~~~~~~~

::

    pip install dropbox django-storages

...And make sure you have the following required settings: ::

    STORAGES = {
        "dbbackup": {
            "BACKEND": "storages.backends.dropbox.DropBoxStorage",
            "OPTIONS": {
                "oauth2_access_token": "my_token",
            },
        },

Available settings
~~~~~~~~~~~~~~~~~~

.. note::

    See `django-storages dropbox official documentation`_ for more details.

.. _`django-storages dropbox official documentation`: https://django-storages.readthedocs.io/en/latest/backends/dropbox.html

**oauth2_access_token** - Required

Your OAuth access token

**root_path**

Jail storage to this directory

FTP
---

To store your database backups on a remote filesystem via [a]FTP, simply
setup the required settings below.

Setup
~~~~~
::

    pip install django-storages


.. warning::

    This storage doesn't use a private connection for communication so don't use it
    if you're not certain about the security of the link between the client and the server.

::

    STORAGES = {
        "dbbackup": {
            "BACKEND": "storages.backends.ftp.FTPStorage",
            "OPTIONS": {
                "location": "ftp://user:pass@server:21",
            },
        },
    }

Settings
~~~~~~~~

**location** -  Required

A FTP URI with optional user, password and port. example: ``'ftp://anonymous@myftp.net'``

Setup
~~~~~

We use FTP backend from Django-Storages (again). ::

    pip install django-storages

Here a simple configuration: ::

    STORAGES = {
        "dbbackup": {
            "BACKEND": "storages.backends.ftp.FTPStorage",
            "OPTIONS": {
                "location": "ftp://myftpserver/",
            },
        },
    }

SFTP
----

To store your database backups on a remote filesystem via SFTP, simply
setup the required settings below.

Setup
~~~~~

This backend is from Django-Storages with the `paramiko`_ backend. ::

    pip install paramiko django-storages

.. _`paramiko`: https://www.paramiko.org/

The following configuration grants SSH server access to the local user: ::

    STORAGES = {
        "dbbackup": {
            "BACKEND": "storages.backends.sftpstorage.SFTPStorage",
            "OPTIONS": {
                'host': 'myserver',
            },
        },
    }



.. _`paramiko SSHClient.connect() documentation`: https://docs.paramiko.org/en/latest/api/client.html#paramiko.client.SSHClient.connect

Available settings
~~~~~~~~~~~~~~~~~~

**host** - Required

Hostname or address of the SSH server

**root_path** - Default ``~/``

Jail storage to this directory

**params** - Default ``{}``

Argument used by method:`paramikor.SSHClient.connect()`.
See `paramiko SSHClient.connect() documentation`_ for details.

**interactive** - Default ``False``

A boolean indicating whether to prompt for a password if the connection cannot
be made using keys, and there is not already a password in ``params``.

**file_mode**

UID of the account that should be set as owner of the files on the remote.

**dir_mode**

GID of the group that should be set on the files on the remote host.

**known_host_file**

Absolute path of known_hosts file, if it isn't set ``"~/.ssh/known_hosts"`` will be used.
