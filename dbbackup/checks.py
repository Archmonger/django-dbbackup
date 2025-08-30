import re
from datetime import datetime

from django.core.checks import Tags, Warning, register

from dbbackup import settings

W001 = Warning(
    "Invalid HOSTNAME parameter",
    hint="Set a non empty string to this settings.DBBACKUP_HOSTNAME",
    id="dbbackup.W001",
)
W002 = Warning(
    "Invalid STORAGE parameter",
    hint="Set a valid path to a storage in settings.DBBACKUP_STORAGE",
    id="dbbackup.W002",
)
W003 = Warning(
    "Invalid FILENAME_TEMPLATE parameter",
    hint="Include {datetime} to settings.DBBACKUP_FILENAME_TEMPLATE",
    id="dbbackup.W003",
)
W004 = Warning(
    "Invalid MEDIA_FILENAME_TEMPLATE parameter",
    hint="Include {datetime} to settings.DBBACKUP_MEDIA_FILENAME_TEMPLATE",
    id="dbbackup.W004",
)
W005 = Warning(
    "Invalid DATE_FORMAT parameter",
    hint="settings.DBBACKUP_DATE_FORMAT can contain only [A-Za-z0-9%_-]",
    id="dbbackup.W005",
)
# W006: Historical - "FAILURE_RECIPIENTS has been deprecated"

W007 = Warning(
    "Invalid FILENAME_TEMPLATE parameter",
    hint="settings.DBBACKUP_FILENAME_TEMPLATE must not contain slashes ('/'). "
    "Did you mean to change the value for 'location'?",
    id="dbbackup.W007",
)
W008 = Warning(
    "Invalid MEDIA_FILENAME_TEMPLATE parameter",
    hint="settings.DBBACKUP_MEDIA_FILENAME_TEMPLATE must not contain slashes ('/')"
    "Did you mean to change the value for 'location'?",
    id="dbbackup.W008",
)

# W009: Historical - "Using removed DBBACKUP_STORAGE parameter"
# W010: Historical - "Using removed DBBACKUP_STORAGE_OPTIONS parameter"


def check_filename_templates():
    return _check_filename_template(
        settings.FILENAME_TEMPLATE,
        W007,
        "db",
    ) + _check_filename_template(
        settings.MEDIA_FILENAME_TEMPLATE,
        W008,
        "media",
    )


def _check_filename_template(filename_template, check_code, content_type) -> list:
    if callable(filename_template):
        params = {
            "servername": "localhost",
            "datetime": datetime.now().strftime(settings.DATE_FORMAT),
            "databasename": "default",
            "extension": "dump",
            "content_type": content_type,
        }
        filename_template = filename_template(params)

    if "/" in filename_template:
        return [check_code]
    return []


@register(Tags.compatibility)
def check_settings(app_configs, **kwargs):
    errors = []
    if not settings.HOSTNAME:
        errors.append(W001)

    if not settings.STORAGE or not isinstance(settings.STORAGE, str):
        errors.append(W002)

    if not callable(settings.FILENAME_TEMPLATE) and "{datetime}" not in settings.FILENAME_TEMPLATE:
        errors.append(W003)

    if not callable(settings.MEDIA_FILENAME_TEMPLATE) and "{datetime}" not in settings.MEDIA_FILENAME_TEMPLATE:
        errors.append(W004)

    if re.search(r"[^A-Za-z0-9%_-]", settings.DATE_FORMAT):
        errors.append(W005)

    errors += check_filename_templates()

    return errors
