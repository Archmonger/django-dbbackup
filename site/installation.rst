Installation
============

Installing on your system
-------------------------

Getting the latest stable release
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    pip install django-dbbackup

Getting the latest release from trunk
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In general, you should not be downloading and installing stuff
directly from repositories -- especially not if you are backing
up sensitive data.

Security is important, bypassing PyPi repositories is a bad habit,
because it will bypass the fragile key signatures authentication
that are at least present when using PyPi repositories.

::

    pip install -e git+https://github.com/Archmonger/django-dbbackup.git#egg=django-dbbackup


Add it in your project
----------------------

In your ``settings.py``, make sure you have the following things: ::

    INSTALLED_APPS = (
        ...
        'dbbackup',  # django-dbbackup
    )

    STORAGES = {
        'dbbackup': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
            'OPTIONS': {
                'location': '/my/backup/dir/',
            },
        },
    }

Create the backup directory: ::

    mkdir /my/backup/dir/

.. note::

    This configuration uses filesystem storage, but you can use any storage
    supported by Django API. See `Storage settings`_ for more information about it.

.. _`Storage settings`: storage.html


Testing that everything worked
------------------------------

Now, you should be able to create your first backup by running: ::

    $ python manage.py dbbackup

If your database was called ``default`` which is the normal Django behaviour
of a single-database project, you should now see a new file in your backup
directory.
