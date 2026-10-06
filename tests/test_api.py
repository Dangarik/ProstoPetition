import pytest
from petitions.models import Petition, Response
from voting.models import Vote


pytestmark = pytest.mark.django_db


def test_created_petition_has_zero_votes_and_server_owned_fields(actors, category, send):
    result = send("post", "/api/petitions/", {
        "title": "Нова петиція", "text": "Текст", "category": category.pk,
        "status": "active", "author": "admin",
    }, actors["author"])
    assert result.status_code == 201
    data = result.json()
    assert data["status"] == "moderation"
    assert data["vote_count"] == 0
    assert data["author"] == "author"
    assert Petition.objects.get(pk=data["id"]).status == "moderation"


@pytest.mark.parametrize("path,method,data", [
    ("/api/categories/999999/", "get", {}),
    ("/api/categories/999999/", "patch", {"name": "Changed"}),
    ("/api/categories/999999/", "delete", {}),
    ("/api/petitions/999999/", "get", {}),
    ("/api/petitions/999999/", "delete", {}),
    ("/api/petitions/999999/vote/", "post", {}),
    ("/api/petitions/999999/status/", "patch", {"status": "active"}),
    ("/api/petitions/999999/response/", "post", {"text": "Response"}),
])
def test_missing_resources_return_json_404(send, actors, path, method, data):
    result = send(method, path, data, actors["admin"])
    assert result.status_code == 404
    assert isinstance(result.json()["detail"], str)


@pytest.mark.parametrize("data", [
    {"title": " ", "text": "Text"}, {"title": "Title", "text": " "},
    {"title": "Title", "text": "Text", "category": 999999},
])
def test_petition_validation_does_not_write_data(send, actors, category, data):
    result = send("post", "/api/petitions/", {"category": category.pk, **data}, actors["author"])
    assert result.status_code == 400
    assert isinstance(result.json(), dict)
    assert not Petition.objects.exists()


@pytest.mark.parametrize("path,method,data", [
    ("/api/categories/", "post", {"name": "Denied"}),
    ("/api/categories/{category}/", "patch", {"name": "Denied"}),
    ("/api/categories/{category}/", "delete", {}),
    ("/api/petitions/{petition}/status/", "patch", {"status": "active"}),
    ("/api/petitions/{petition}/response/", "post", {"text": "Denied"}),
    ("/api/admin/petitions/", "get", {}),
])
def test_admin_operations_deny_regular_user(send, actors, petition, path, method, data):
    result = send(method, path.format(category=petition.category_id, petition=petition.pk), data, actors["voter"])
    assert result.status_code == 403
    assert isinstance(result.json()["detail"], str)
    petition.refresh_from_db()
    assert petition.status == "moderation"
    assert not Response.objects.exists()


@pytest.mark.parametrize("method,path,data", [
    ("patch", "/api/categories/{category}/", {"vote_threshold": 10}),
    ("delete", "/api/petitions/{petition}/", {}),
    ("post", "/api/petitions/{petition}/response/", {"text": "Response"}),
])
def test_mutations_require_csrf(send, actors, petition, method, path, data):
    result = send(method, path.format(category=petition.category_id, petition=petition.pk),
                  data, actors["admin"], csrf=False)
    assert result.status_code == 403
    assert isinstance(result.json()["detail"], str)
    assert Petition.objects.filter(pk=petition.pk).exists()


def test_guest_cannot_vote(send, petition):
    petition.status = "active"
    petition.save()
    assert send("post", f"/api/petitions/{petition.pk}/vote/").status_code == 403
    assert not Vote.objects.exists()


@pytest.mark.parametrize("data", [{"status": "unknown"}, {"status": "active", "reason": 123}])
def test_status_validation(send, petition, actors, data):
    assert send("patch", f"/api/petitions/{petition.pk}/status/", data, actors["admin"]).status_code == 400
    petition.refresh_from_db()
    assert petition.status == "moderation"


@pytest.mark.parametrize("text", ["", " ", 123, None])
def test_response_validation(send, petition, actors, text):
    petition.status = "in_review"
    petition.save()
    response = send("post", f"/api/petitions/{petition.pk}/response/", {"text": text}, actors["admin"])
    assert response.status_code == 400
    assert not Response.objects.exists()


def test_response_before_review_is_conflict(send, petition, actors):
    result = send("post", f"/api/petitions/{petition.pk}/response/", {"text": "Response"}, actors["admin"])
    assert result.status_code == 409
    assert not Response.objects.exists()


@pytest.mark.parametrize("query", ["category=bad", "status=bad", "page=9999"])
def test_list_rejects_invalid_filters_or_missing_page(send, query):
    result = send("get", "/api/petitions/?" + query)
    assert result.status_code == (404 if query.startswith("page") else 400)
