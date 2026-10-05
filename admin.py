from django.contrib import admin

from django.contrib import admin
from django.test import SimpleTestCase
from .users.models import Petition

class AdminAutoDiscoverTests(SimpleTestCase):
    def test_double_call_autodiscover(self):
        with self.assertRaisesMessage(Exception, "Bad admin module"):
            admin.autodiscover()
        with self.assertRaisesMessage(Exception, "Bad admin module"):
            admin.autodiscover()


