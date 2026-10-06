from datetime import timedelta
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from petitions.models import Category, Petition


@pytest.fixture
def actors(db):
    User = get_user_model()
    return {
        name: User.objects.create_user(
            username=name, email=f"{name}@example.com", password="StrongPass!123",
            is_staff=name == "admin",
        )
        for name in ("author", "voter", "admin")
    }


@pytest.fixture
def category(db):
    return Category.objects.create(name="Освіта", vote_threshold=5)


@pytest.fixture
def petition(actors, category):
    return Petition.objects.create(
        title="Чиста вода", text="Програма чистої води", author=actors["author"],
        category=category, deadline=timezone.now() + timedelta(days=5),
    )


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def send(api_client):
    def request(method, path, data=None, user=None, csrf=True):
        api_client.logout()
        if user is not None:
            api_client.force_login(user)
        token = api_client.get("/api/auth/csrf/").json()["csrfToken"]
        headers = {"HTTP_X_CSRFTOKEN": token} if csrf else {}
        if method == "get":
            return api_client.get(path, **headers)
        return getattr(api_client, method)(path, data=data or {}, format="json", **headers)
    return request
