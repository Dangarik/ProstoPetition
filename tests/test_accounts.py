import pytest
from django.contrib.auth import get_user_model


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("field,value", [("username", "author"), ("email", "AUTHOR@EXAMPLE.COM")])
def test_registration_rejects_duplicate_identity(actors, send, field, value):
    data = {"username": "newuser", "email": "new@example.com", "password": "StrongPass!123"}
    data[field] = value
    result = send("post", "/api/auth/register/", data)
    assert result.status_code == 400
    assert result.headers["Content-Type"].startswith("application/json")
    assert get_user_model().objects.count() == 3


@pytest.mark.parametrize("path", ["/api/auth/register/", "/api/auth/login/"])
@pytest.mark.parametrize("body", [b"{", b"[]", b"null"])
def test_auth_rejects_invalid_json(api_client, path, body):
    token = api_client.get("/api/auth/csrf/").json()["csrfToken"]
    response = api_client.post(path, data=body, content_type="application/json", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 400
    assert isinstance(response.json()["detail"], str)


def test_wrong_password_does_not_create_a_session(actors, send, api_client):
    result = send("post", "/api/auth/login/", {"username": "author", "password": "wrong"})
    assert result.status_code == 400
    assert api_client.get("/api/auth/profile/").status_code == 403


@pytest.mark.parametrize("data", [
    {}, {"username": "author"}, {"username": [], "password": "StrongPass!123"},
    {"username": "author", "password": []}, {"username": "author", "password": 42},
])
def test_login_rejects_invalid_field_types(actors, send, data):
    response = send("post", "/api/auth/login/", data)
    assert response.status_code == 400
    assert isinstance(response.json()["detail"], str)


@pytest.mark.parametrize("data", [
    {}, {"username": " ", "email": "a@example.com", "password": "StrongPass!123"},
    {"username": "new", "email": "not-email", "password": "StrongPass!123"},
    {"username": "new", "email": "a@example.com", "password": "123"},
])
def test_registration_validation_does_not_create_users(send, data):
    response = send("post", "/api/auth/register/", data)
    assert response.status_code == 400
    assert get_user_model().objects.count() == 0


def test_guest_profile_and_logout_are_forbidden(send):
    assert send("get", "/api/auth/profile/").status_code == 403
    assert send("post", "/api/auth/logout/").status_code == 403


def test_csrf_endpoint_sets_cookie_and_auth_methods_are_limited(api_client):
    response = api_client.get("/api/auth/csrf/")
    assert response.status_code == 200
    assert isinstance(response.json()["csrfToken"], str)
    assert "csrftoken" in response.cookies
    assert api_client.get("/api/auth/login/").status_code == 405
