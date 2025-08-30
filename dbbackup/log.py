import logging

from django.utils.log import AdminEmailHandler


class DbbackupAdminEmailHandler(AdminEmailHandler):
    def send_mail(self, subject, message, *args, **kwargs):
        from dbbackup import utils

        utils.mail_admins(subject, message, *args, connection=self.connection(), **kwargs)


class MailEnabledFilter(logging.Filter):
    def filter(self, record):
        from dbbackup.settings import SEND_EMAIL

        return SEND_EMAIL


def load():
    mail_admins_handler = DbbackupAdminEmailHandler(include_html=True)
    mail_admins_handler.setLevel(logging.ERROR)
    mail_admins_handler.addFilter(MailEnabledFilter())

    logger = logging.getLogger("dbbackup")
    logger.setLevel(logging.INFO)
    logger.handlers = [mail_admins_handler]
