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
        self.category = Category.objects.create(name="Освіта", vote_threshold=2)
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
        data = {"title": "Нові дороги", "text": "Ремонт дороги", "category": self.category.id}
        self.assertEqual(self.send("post", "/api/petitions/", data).status_code, 403)
        before = timezone.now()
        created = self.send("post", "/api/petitions/", data, self.author)
        after = timezone.now()
        self.assertEqual(created.status_code, 201)
        deadline = timezone.datetime.fromisoformat(created.json()["deadline"])
        self.assertGreaterEqual(deadline, self.category.maximum_deadline(before))
        self.assertLessEqual(deadline, self.category.maximum_deadline(after))
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
        self.assertEqual(self.send("patch", status_url, {"status": "active", "vote_threshold": 2}, user=self.admin).status_code, 400)
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

    def test_category_duration_and_vote_threshold(self):
        category_url = "/api/categories/"
        self.assertEqual(self.send("post", category_url, {
            "name": "Без порогу", "max_years": 0, "max_months": 0, "max_days": 10,
        }, user=self.admin).status_code, 400)
        self.assertEqual(self.send("post", category_url, {
            "name": "Від’ємний поріг", "max_years": 0, "max_months": 0, "max_days": 10,
            "vote_threshold": -1,
        }, user=self.admin).status_code, 400)
        self.assertEqual(self.send("post", category_url, {
            "name": "Неправильна", "max_years": -1, "max_months": 0, "max_days": 0, "vote_threshold": 2,
        }, user=self.admin).status_code, 400)
        self.assertEqual(self.send("post", category_url, {
            "name": "Нуль", "max_years": 0, "max_months": 0, "max_days": 0, "vote_threshold": 2,
        }, user=self.admin).status_code, 400)
        made = self.send("post", category_url, {
            "name": "Коротка", "max_years": 0, "max_months": 0, "max_days": 10, "vote_threshold": 2,
        }, user=self.admin)
        self.assertEqual(made.status_code, 201)
        category_id = made.json()["id"]
        self.assertEqual(self.send("patch", f"{category_url}{category_id}/", {
            "max_days": -1,
        }, user=self.admin).status_code, 400)
        petition_data = {"title": "Нова", "text": "Текст", "category": category_id}
        self.assertEqual(self.send("post", "/api/petitions/", {
            **petition_data, "deadline": (timezone.now() + timedelta(days=5)).isoformat(),
        }, user=self.author).status_code, 400)
        self.assertEqual(self.send("post", "/api/petitions/", {
            **petition_data, "vote_threshold": 1,
        }, user=self.author).status_code, 400)
        self.assertEqual(self.send("post", "/api/petitions/", {
            **petition_data, "vote_threshold": 1,
        }, user=self.admin).status_code, 400)
        before = timezone.now()
        created = self.send("post", "/api/petitions/", petition_data, user=self.author)
        after = timezone.now()
        self.assertEqual(created.status_code, 201)
        deadline = timezone.datetime.fromisoformat(created.json()["deadline"])
        category = Category.objects.get(pk=category_id)
        self.assertGreaterEqual(deadline, category.maximum_deadline(before))
        self.assertLessEqual(deadline, category.maximum_deadline(after))
        self.assertEqual(created.json()["vote_threshold"], 2)
        petition_id = created.json()["id"]
        status_url = f"/api/petitions/{petition_id}/status/"
        self.assertEqual(self.send("patch", status_url, {
            "status": "active", "vote_threshold": -1,
        }, user=self.admin).status_code, 400)
        activated = self.send("patch", status_url, {"status": "active"}, user=self.admin)
        self.assertEqual(activated.status_code, 200)
        self.assertEqual(activated.json()["vote_threshold"], 2)
        first = self.send("post", f"/api/petitions/{petition_id}/vote/", user=self.voter)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["status"], "active")
        second = self.send("post", f"/api/petitions/{petition_id}/vote/", user=self.author)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.json()["vote_count"], 2)
        self.assertEqual(second.json()["status"], "in_review")
        self.assertFalse(second.json()["is_active"])
        self.assertEqual(self.send("post", f"/api/petitions/{petition_id}/vote/", user=self.admin).status_code, 409)
        self.assertEqual(Petition.objects.get(pk=petition_id).status, "in_review")

    def test_setting_threshold_for_existing_active_petition(self):
        petition = self.create_petition(status=Petition.Status.ACTIVE)
        self.assertEqual(petition.category.vote_threshold, 2)
        self.assertEqual(self.send("post", f"/api/petitions/{petition.pk}/vote/", user=self.voter).status_code, 201)
        changed = self.send("patch", f"/api/categories/{self.category.pk}/", {
            "vote_threshold": 1,
        }, user=self.admin)
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.json()["vote_threshold"], 1)
        petition.refresh_from_db()
        self.assertEqual(petition.status, "in_review")
        self.assertEqual(self.send("get", f"/api/petitions/{petition.pk}/").json()["vote_threshold"], 1)

    def test_legacy_category_needs_admin_threshold_before_voting(self):
        category = Category.objects.create(name="Стара категорія")
        petition = Petition.objects.create(
            title="Стара активна", text="Текст", author=self.author, category=category,
            deadline=timezone.now() + timedelta(days=5), status=Petition.Status.ACTIVE)
        self.assertFalse(self.send("get", f"/api/petitions/{petition.pk}/").json()["is_active"])
        self.assertEqual(self.send("post", f"/api/petitions/{petition.pk}/vote/", user=self.voter).status_code, 409)
        self.assertEqual(self.send("patch", f"/api/categories/{category.pk}/", {
            "vote_threshold": 2,
        }, user=self.admin).status_code, 200)
        self.assertTrue(self.send("get", f"/api/petitions/{petition.pk}/").json()["is_active"])


