from django.core.management.base import BaseCommand
from petitions.services import expire_petitions


class Command(BaseCommand):
    help = "Позначає прострочені активні петиції як expired."

    def handle(self, *args, **options):
        count = expire_petitions()
        self.stdout.write(self.style.SUCCESS(f"Завершено петицій: {count}"))
