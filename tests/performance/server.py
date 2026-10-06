import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["DJANGO_SETTINGS_MODULE"] = "ProstoPetition.test_settings"
os.environ["DJANGO_DEBUG"] = "1"

import django
from django.conf import settings
from django.core.management import call_command


def main():
    with TemporaryDirectory(prefix="prostopetition-load-") as directory:
        settings.DATABASES["default"]["NAME"] = str(Path(directory) / "test.sqlite3")
        django.setup()
        call_command("migrate", verbosity=0)
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from petitions.models import Category, Petition
        author = get_user_model().objects.create_user(username="load-author")
        category = Category.objects.create(name="Load test", vote_threshold=100)
        Petition.objects.bulk_create([
            Petition(title=f"Load petition {number}", text="Temporary load-test data",
                     author=author, category=category, status=Petition.Status.ACTIVE,
                     deadline=timezone.now() + timedelta(days=1))
            for number in range(30)
        ])
        call_command("runserver", "127.0.0.1:8001", use_reloader=False, verbosity=0)


if __name__ == "__main__":
    main()
