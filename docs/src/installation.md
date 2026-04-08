---
hide:
    - navigation
---

## Installing on your system

### Getting the latest stable release

```bash
pip install django-dbbackup
```

??? tip "Alternate: Install the latest from GitHub"

    In general, you should not be downloading and installing stuff
    directly from repositories. Security is important; bypassing PyPI repositories is a bad habit.

    However, if you are willing to accept the risks of installing directly from GitHub, you can do so with pip:

    ```bash
    pip install -e git+https://github.com/Archmonger/django-dbbackup.git#egg=django-dbbackup
    ```

## Configure your project

!!! note

    The following example uses filesystem storage, but you can use any storage supported by Django API. See [Storage settings](storage.md) for more information about it.

In your `settings.py`, make sure you have `dbbackup` in your `INSTALLED_APPS` have configured a storage backend:

```python
INSTALLED_APPS = (
    ... ,
    'dbbackup',  # django-dbbackup
)

STORAGES = {
    ...,
    'dbbackup': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
        'OPTIONS': {
            'location': '/my/backup/dir/',
        },
    },
}
```

Then, create the backup directory:

```bash
mkdir /my/backup/dir/
```

## Testing that everything worked

Now, you should be able to create your first backup by running:

```bash
python manage.py dbbackup
```

If your database was called `default` which is the normal Django behavior
of a single-database project, you should now see a new file in your backup
directory.
