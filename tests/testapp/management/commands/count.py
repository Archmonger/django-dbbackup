from django.core.management.base import BaseCommand

from tests.testapp.models import CharModel


class Command(BaseCommand):
    help = "Count things"

    def handle(self, **options):
        self.stdout.write(str(CharModel.objects.count()))
