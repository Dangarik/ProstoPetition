from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone
from petitions.models import Category, Petition, Response

class AdminTests(TestCase):
    def test_admin_adds_petition_with_category_threshold(self):
        admin = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="StrongPass!123")
        category = Category.objects.create(name="Освіта", vote_threshold=3)
        client = Client(enforce_csrf_checks=True)
        client.force_login(admin)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        data = {"title": "Створена адміном", "text": "Текст", "author": admin.pk,
                "category": category.pk}
        before = timezone.now()
        response = client.post("/admin/petitions/petition/add/", data, HTTP_X_CSRFTOKEN=token)
        after = timezone.now()
        self.assertEqual(response.status_code, 302)
        petition = Petition.objects.get(title="Створена адміном")
        self.assertEqual(petition.category.vote_threshold, 3)
        self.assertEqual(petition.status, "moderation")
        self.assertGreaterEqual(petition.deadline, category.maximum_deadline(before))
        self.assertLessEqual(petition.deadline, category.maximum_deadline(after))

    def test_moderation_and_response_through_admin(self):
        admin = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="StrongPass!123")
        author = get_user_model().objects.create_user(username="author", password="StrongPass!123")
        category = Category.objects.create(name="Освіта", vote_threshold=2)
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

    def test_category_threshold_change_moves_existing_petition_to_review(self):
        admin = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="StrongPass!123")
        category = Category.objects.create(name="Освіта", vote_threshold=2)
        petition = Petition.objects.create(
            title="Петиція", text="Текст", author=admin, category=category,
            deadline=timezone.now() + timedelta(days=5), status=Petition.Status.ACTIVE)
        from voting.models import Vote
        Vote.objects.create(user=admin, petition=petition)
        client = Client(enforce_csrf_checks=True)
        client.force_login(admin)
        token = client.get("/api/auth/csrf/").json()["csrfToken"]
        response = client.post(f"/admin/petitions/category/{category.pk}/change/", {
            "name": category.name, "vote_threshold": 1, "max_years": 1,
            "max_months": 0, "max_days": 0,
        }, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 302)
        petition.refresh_from_db()
        self.assertEqual(petition.status, Petition.Status.IN_REVIEW)

