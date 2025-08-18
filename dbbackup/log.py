import logging

import django
from django.utils.log import AdminEmailHandler


class DbbackupAdminEmailHandler(AdminEmailHandler):
    def emit(self, record):
        # Monkey patch for old Django versions without send_mail method
        if django.VERSION < (1, 8):
            from . import utils

            django.core.mail.mail_admins = utils.mail_admins
        super().emit(record)

    def send_mail(self, subject, message, *args, **kwargs):
        from . import utils

        utils.mail_admins(subject, message, *args, connection=self.connection(), **kwargs)


class MailEnabledFilter(logging.Filter):
    def filter(self, record):
        from .settings import SEND_EMAIL

        return SEND_EMAIL


def load():
    mail_admins_handler = DbbackupAdminEmailHandler(include_html=True)
    mail_admins_handler.setLevel(logging.ERROR)
    mail_admins_handler.addFilter(MailEnabledFilter())

    logger = logging.getLogger("dbbackup")
    logger.setLevel(logging.INFO)
    logger.handlers = [mail_admins_handler]
