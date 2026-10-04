from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone
from .models import Category, Petition, Response

class AdminTests(TestCase):
    def test_moderation_and_response_through_admin(self):
        admin = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="StrongPass!123")
        author = get_user_model().objects.create_user(username="author", password="StrongPass!123")
        category = Category.objects.create(name="Освіта")
        petition = Petition.objects.create(
            title="Нова петиція", text="Текст", author=author, category=category,
            deadline=timezone.now() + timedelta(days=5))
        client = Client(enforce_csrf_checks=True)
        client.force_login(admin)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        url = f"/admin/petitions/petition/{petition.pk}/change/"
        response = client.post(url, {"status": "active", "moderation_reason": ""},
                               HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 302)
        petition.refresh_from_db()
        self.assertEqual(petition.status, "active")
        response = client.post(url, {"status": "in_review", "moderation_reason": ""},
                               HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 302)
        petition.refresh_from_db()
        self.assertEqual(petition.status, "in_review")
        response = client.post("/admin/petitions/response/add/",
                               {"petition": petition.id, "text": "Рішення"},
                               HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 302)
        petition.refresh_from_db()
        self.assertEqual(petition.status, "answered")
        self.assertEqual(Response.objects.get(petition=petition).author, admin)

