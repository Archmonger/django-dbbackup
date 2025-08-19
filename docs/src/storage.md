# Storage settings

One of the most helpful features of django-dbbackup is the ability to store
and retrieve backups from local or remote storage. This functionality is
mainly based on the Django Storage API and extends its possibilities.

Configure backup storage via the `STORAGES` setting using the key `'dbbackup'`.
`BACKEND` is a dotted path to a Django storage class. For example use
`'django.core.files.storage.FileSystemStorage'` for the local filesystem. A
few common third party backends (via `django-storages`) are [documented below](#file-system-storage).

```python
STORAGES = {
    "dbbackup": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": "/my/backup/dir/",
        },
    },
}
```

For more granularity, per backend options go into the nested `OPTIONS` dict:

```python
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
```

!!! warning
Do not configure backup storage with the same configuration as your media
files as you'll risk sharing backups inside public directories.

If no explicit `STORAGES['dbbackup']` is provided the default File System Storage
is used (pointing at your project media root). Consider isolating backups in a
dedicated directory with restricted permissions. Browse additional providers
at [Django Packages](https://djangopackages.org/grids/g/storage-backends/).

!!! note
Storing backups to local disk may also be useful for Dropbox if you
already have the official Dropbox client installed on your system.

## File system storage

### Setup

To store your backups on the local file system, simply set up the required
settings below.

```python
STORAGES = {
    "dbbackup": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": "/my/backup/dir/",
        },
    },
}
```

### Settings

**`location`**

Absolute path to the directory that will hold the files.

**`file_permissions_mode`**

The file system permissions that the file will receive when it is saved.

**`directory_permissions_mode`**

The file system permissions that the directory will receive when it is saved.

See [FileSystemStorage's documentation](https://docs.djangoproject.com/en/stable/ref/files/storage/#the-filesystemstorage-class) for a full list of available settings.

## Google cloud storage

Our backend for Google cloud storage uses django-storages.

### Setup

Create a Google Cloud project and bucket, then install:

```bash
pip install django-storages[google]
```

Add the following to settings (only `bucket_name` is strictly required). See
the [django-storages docs](https://django-storages.readthedocs.io/en/latest/backends/gcloud.html) for advanced options.

```python
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
```

## Amazon S3

Our S3 backend uses Django Storages which uses [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html).

### Setup

Create an AWS account and S3 bucket, then install dependencies:

```bash
pip install django-storages[boto3]
```

Add this snippet to settings:

```python
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
```

### Settings

!!! note
See the [Django Storage S3 storage official documentation](https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html) for all options.

    The options listed here are a selection of dictionary keys returned by
    `get_default_settings` in django-storages' [`storages/backends/s3boto3.py`](https://github.com/jschneier/django-storages/blob/master/storages/backends/s3boto3.py#L293-L324),
    which allows us to write nicer code compared to using the `AWS_` prefixed
    settings.

**`access_key`** - Required

Your AWS access key. Create one via the IAM console; avoid using root keys.

**`secret_key`** - Required

Your Amazon Web Services secret access key, as a string.

**`bucket_name`** - Required

Name of the existing bucket to store backups.

**`region_name`** - Optional

AWS region for the bucket (e.g. `'us-east-1'`).

**`endpoint_url`** - Optional

Override the endpoint (for S3-compatible services like MinIO). Must include
protocol, e.g. `https://minio.internal:9000`.

If you set a custom endpoint also set **`region_name`**.

**`default_acl`** - Required

Allowed values: `'private'` or `'public'`. Use `'private'` for backups.

_NOTE: This value will be removed in a future version of django-storages._
See their [CHANGELOG](https://github.com/jschneier/django-storages/blob/master/CHANGELOG.rst) for details.

**`location`** - Optional

Prefix inside the bucket; include trailing slash. Example:
`location: 'backups/prod/'`.

## Dropbox

Create a Dropbox app and obtain an access token, then configure the backend.

### Setup

First, configure your Dropbox account by following these steps:

1. Login to Dropbox and navigate to [Developers » MyApps](https://www.dropbox.com/developers/apps).

2. Click the button to create a new app and name it whatever you like.
   As an example, I named mine 'Website Backups'.

3. After your app is created, note the options button and more
   importantly the 'App Key' and 'App Secret' values inside. You'll need
   those later.

Then, configure your Django project by installing the required
dependencies:

```bash
pip install dropbox django-storages
```

And make sure you have the following required settings:

```python
STORAGES = {
    "dbbackup": {
        "BACKEND": "storages.backends.dropbox.DropBoxStorage",
        "OPTIONS": {
            "oauth2_access_token": "my_token",
        },
    },
}
```

### Settings

!!! note
See [django-storages dropbox official documentation](https://django-storages.readthedocs.io/en/latest/backends/dropbox.html) for more details.

**`oauth2_access_token`** - Required

OAuth 2 access token generated for the app.

**`root_path`**

Restrict storage operations to this folder prefix.

## FTP

To store your database backups on a remote filesystem via FTP, simply
set up the required settings below.

### Setup

```bash
pip install django-storages
```

!!! warning
This storage doesn't use a private connection for communication, so don't use it
if you're not certain about the security of the link between the client and the server.

```python
STORAGES = {
    "dbbackup": {
        "BACKEND": "storages.backends.ftp.FTPStorage",
        "OPTIONS": {
            "location": "ftp://user:pass@server:21",
        },
    },
}
```

### Settings

**`location`** - Required

FTP URI including optional credentials and port. Example:
`ftp://user:pass@ftp.example.com:21`.

## SFTP

To store your database backups on a remote filesystem via SFTP, simply
set up the required settings below.

### Setup

This backend is from django-storages with the [Paramiko](https://www.paramiko.org/) backend.

```bash
pip install paramiko django-storages
```

The following configuration grants SSH server access to the local user:

```python
STORAGES = {
    "dbbackup": {
        "BACKEND": "storages.backends.sftpstorage.SFTPStorage",
        "OPTIONS": {
            'host': 'myserver',
        },
    },
}
```

### Settings

**`host`** - Required

Host name or address of the SSH server.

**`root_path`** - Default `~/`

Jail storage to this directory.

**`params`** - Default `{}`

Argument used by method: `paramiko.SSHClient.connect()`.
See [paramiko SSHClient.connect() documentation](https://docs.paramiko.org/en/latest/api/client.html#paramiko.client.SSHClient.connect) for details.

**`interactive`** - Default `False`

A boolean indicating whether to prompt for a password if the connection cannot
be made using keys and there is not already a password in `params`.

**`file_mode`**

UID of the account that should be set as owner of the files on the remote.

**`dir_mode`**

GID of the group that should be set on the files on the remote host.

**`known_host_file`**

Absolute path of known_hosts file; if it isn't set `"~/.ssh/known_hosts"` will be used.
