import os
os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret")
from .settings import *
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}


