---
hide:
    - navigation
---

## Step 1: Install from PyPI

You can install the latest stable release from PyPI with pip.

```bash
pip install django-dbbackup
```

??? tip "Alternative: Install the latest from GitHub"

    In general, you should not be downloading and installing stuff
    directly from repositories. Security is important; bypassing PyPI repositories is a bad habit.

    However, if you are willing to accept the risks of installing directly from GitHub, you can do so with pip:

    ```bash
    pip install -e git+https://github.com/Archmonger/django-dbbackup.git#egg=django-dbbackup
    ```

## Step 2: Configure `settings.py`

In your `settings.py`, make sure you have `dbbackup` in your `INSTALLED_APPS` have configured a storage backend.

```python
INSTALLED_APPS = (
    ... ,
    'dbbackup',
)
```

## Step 3: Choose a storage backend

You need to configure at least one storage backend for database/media backups. This is done by adding a `dbbackup` entry to the `STORAGES` setting in your `settings.py`.

```python
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

??? tip "Alternative: Use a different storage system"

    This example uses filesystem storage, but there are several other options available. See [Storage settings](storage.md) for more information.

## Step 4: Create your first backup

Now, you should be able to create your first backup by running the Django management command.

```bash
python manage.py dbbackup
```

You should now see a new file in your backup directory.
