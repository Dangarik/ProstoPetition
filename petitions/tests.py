from datetime import timedelta
import json
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone
from .models import Category, Petition, Response

class ApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.author = User.objects.create_user(username="author", email="author@example.com", password="StrongPass!123")
        self.voter = User.objects.create_user(username="voter", email="voter@example.com", password="StrongPass!123")
        self.admin = User.objects.create_superuser(username="admin", email="admin@example.com", password="StrongPass!123")
        self.category = Category.objects.create(name="Освіта")
        self.client = Client(enforce_csrf_checks=True)
        self.token = self.client.get("/api/auth/csrf/").json()["csrfToken"]

    def send(self, method, path, data=None, user=None, csrf=True):
        if user:
            self.client.force_login(user)
            self.token = self.client.get("/api/auth/csrf/").json()["csrfToken"]
        else:
            self.client.logout()
            self.token = self.client.get("/api/auth/csrf/").json()["csrfToken"]
        headers = {"HTTP_X_CSRFTOKEN": self.token} if csrf else {}
        return self.client.get(path, **headers) if method == "get" else getattr(self.client, method)(path, data=json.dumps(data or {}), content_type="application/json", **headers)

    def create_petition(self, status=Petition.Status.MODERATION, deadline=None, title="Чиста вода"):
        return Petition.objects.create(
            title=title, text="Програма чистої води", author=self.author, category=self.category,
            status=status, deadline=deadline or timezone.now() + timedelta(days=10),
        )

    def test_registration_login_profile_logout_and_csrf(self):
        data = {"username": "newuser", "email": "new@example.com", "password": "StrongPass!123"}
        denied = self.client.post("/api/auth/register/", data=json.dumps(data), content_type="application/json")
        self.assertEqual(denied.status_code, 403)
        made = self.client.post("/api/auth/register/", data=json.dumps(data),
                                content_type="application/json", HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(made.status_code, 201)
        self.assertEqual(self.client.get("/api/auth/profile/").status_code, 200)
        token = self.client.get("/api/auth/csrf/").json()["csrfToken"]
        self.assertEqual(self.client.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=token).status_code, 200)
        token = self.client.get("/api/auth/csrf/").json()["csrfToken"]
        login = self.client.post("/api/auth/login/", data=json.dumps({"username": "newuser", "password": "StrongPass!123"}),
                                 content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(login.status_code, 200)
        token = self.client.get("/api/auth/csrf/").json()["csrfToken"]
        self.assertEqual(self.client.post("/api/auth/register/", data=json.dumps(data),
                                content_type="application/json", HTTP_X_CSRFTOKEN=token).status_code, 400)

    def test_create_visibility_search_filter_sort_and_delete(self):
        data = {"title": "Нові дороги", "text": "Ремонт дороги", "category": self.category.id,
                "deadline": (timezone.now() + timedelta(days=10)).isoformat()}
        self.assertEqual(self.send("post", "/api/petitions/", data).status_code, 403)
        created = self.send("post", "/api/petitions/", data, self.author)
        self.assertEqual(created.status_code, 201)
        pk = created.json()["id"]
        self.assertEqual(created.json()["status"], "moderation")
        self.assertEqual(self.send("get", "/api/petitions/").json()["count"], 0)
        self.assertEqual(self.send("get", f"/api/petitions/{pk}/").status_code, 404)
        self.assertEqual(self.send("get", f"/api/petitions/{pk}/", user=self.author).status_code, 200)
        self.assertEqual(self.send("delete", f"/api/petitions/{pk}/", user=self.voter).status_code, 403)
        self.assertEqual(self.send("delete", f"/api/petitions/{pk}/", user=self.author).status_code, 204)
        visible = self.create_petition(status="active", title="Вода в місті")
        self.assertEqual(self.send("get", "/api/petitions/?search=води").json()["count"], 1)
        self.assertEqual(self.send("get", f"/api/petitions/?category={self.category.id}&status=active&ordering=-vote_count").json()["results"][0]["id"], visible.id)
        self.assertEqual(self.send("get", "/api/petitions/?ordering=wrong").status_code, 400)

    def test_vote_state_uniqueness_count_and_moderation(self):
        petition = self.create_petition()
        vote_url = f"/api/petitions/{petition.id}/vote/"
        status_url = f"/api/petitions/{petition.id}/status/"
        self.assertEqual(self.send("post", vote_url, user=self.voter).status_code, 409)
        self.assertEqual(self.send("patch", status_url, {"status": "active"}, user=self.author).status_code, 403)
        self.assertEqual(self.send("patch", status_url, {"status": "active"}, user=self.admin).status_code, 200)
        self.assertEqual(self.send("post", vote_url, user=self.voter, csrf=False).status_code, 403)
        first = self.send("post", vote_url, user=self.voter)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["vote_count"], 1)
        self.assertEqual(self.send("post", vote_url, user=self.voter).status_code, 409)
        self.assertEqual(self.send("delete", f"/api/petitions/{petition.id}/", user=self.author).status_code, 409)
        self.assertEqual(self.send("patch", status_url, {"status": "in_review"}, user=self.admin).status_code, 200)
        self.assertEqual(self.send("post", vote_url, user=self.author).status_code, 409)
        self.assertEqual(self.send("post", f"/api/petitions/{petition.id}/response/",
                                   {"text": "Офіційна відповідь"}, user=self.admin).status_code, 201)
        petition.refresh_from_db()
        self.assertEqual(petition.status, "answered")
        self.assertEqual(Response.objects.get(petition=petition).author, self.admin)
        self.assertEqual(self.send("post", f"/api/petitions/{petition.id}/response/",
                                   {"text": "Ще одна"}, user=self.admin).status_code, 409)

    def test_deadline_reasons_stats_and_private_visibility(self):
        expired = self.create_petition(status="active", deadline=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.send("post", f"/api/petitions/{expired.id}/vote/", user=self.voter).status_code, 409)
        pending = self.create_petition(title="Закрита тема")
        url = f"/api/petitions/{pending.id}/status/"
        self.assertEqual(self.send("patch", url, {"status": "rejected"}, user=self.admin).status_code, 409)
        self.assertEqual(self.send("patch", url, {"status": "rejected", "reason": "Порушення правил"}, user=self.admin).status_code, 200)
        self.assertEqual(self.send("get", f"/api/petitions/{pending.id}/").status_code, 404)
        self.assertEqual(self.send("get", "/api/admin/statistics/", user=self.author).status_code, 403)
        stats = self.send("get", "/api/admin/statistics/", user=self.admin)
        self.assertEqual(stats.status_code, 200)
        self.assertEqual(stats.json()["by_status"]["rejected"], 1)

    def test_vote_database_constraint(self):
        from django.db import IntegrityError, transaction
        from voting.models import Vote
        petition = self.create_petition(status="active")
        Vote.objects.create(user=self.voter, petition=petition)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Vote.objects.create(user=self.voter, petition=petition)


