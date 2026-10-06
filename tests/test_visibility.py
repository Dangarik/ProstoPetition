from datetime import timedelta
import pytest
from django.utils import timezone
from voting.models import Vote


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("state", ["expired", "rejected"])
def test_admin_can_hide_and_restore_without_losing_data(state, petition, actors, send):
    petition.status = state
    petition.save()
    Vote.objects.create(petition=petition, user=actors["voter"])
    url = f"/api/petitions/{petition.pk}/visibility/"
    for hidden in (True, False):
        result = send("patch", url, {"is_hidden": hidden}, actors["admin"])
        assert result.status_code == 200
        assert result.json()["is_hidden"] is hidden
        petition.refresh_from_db()
        assert petition.status == state
        assert petition.votes.count() == 1
        assert petition.text == "Програма чистої води"
        for user in (None, actors["voter"], actors["author"], actors["admin"]):
            public = send("get", f"/api/petitions/?search={petition.title}", user=user).json()
            expected = not hidden and (state == "expired" or user == actors["admin"])
            assert public["count"] == int(expected)
        profile = send("get", "/api/auth/profile/", user=actors["author"]).json()
        assert profile["petitions"][0]["is_hidden"] is hidden
        admin = send("get", f"/api/admin/petitions/?status={state}", user=actors["admin"]).json()
        assert admin["results"][0]["is_hidden"] is hidden
        assert send("get", f"/api/petitions/{petition.pk}/", user=actors["author"]).status_code == 200
        assert send("get", f"/api/petitions/{petition.pk}/", user=actors["admin"]).status_code == 200
        assert send("get", f"/api/petitions/{petition.pk}/").status_code == (200 if state == "expired" and not hidden else 404)


@pytest.mark.parametrize("user", [None, "author", "voter"])
def test_only_admin_can_hide(user, petition, actors, send):
    petition.status = "expired"
    petition.save()
    assert send("patch", f"/api/petitions/{petition.pk}/visibility/", {"is_hidden": True}, actors.get(user)).status_code == 403
    petition.refresh_from_db()
    assert not petition.is_hidden


@pytest.mark.parametrize("state", ["active", "moderation", "in_review", "answered", "closed"])
def test_cannot_hide_other_states(state, petition, actors, send):
    petition.status = state
    petition.save()
    assert send("patch", f"/api/petitions/{petition.pk}/visibility/", {"is_hidden": True}, actors["admin"]).status_code == 409
    petition.refresh_from_db()
    assert not petition.is_hidden


@pytest.mark.parametrize("value", ["false", 1, None])
def test_visibility_requires_boolean(value, petition, actors, send):
    assert send("patch", f"/api/petitions/{petition.pk}/visibility/", {"is_hidden": value}, actors["admin"]).status_code == 400


def test_visibility_requires_csrf_and_existing_resource(petition, actors, send):
    assert send("patch", f"/api/petitions/{petition.pk}/visibility/", {"is_hidden": True}, actors["admin"], csrf=False).status_code == 403
    assert send("patch", "/api/petitions/999999/visibility/", {"is_hidden": True}, actors["admin"]).status_code == 404


def test_overdue_active_is_expired_before_hiding(petition, actors, send):
    petition.status = "active"
    petition.deadline = timezone.now() - timedelta(seconds=1)
    petition.save()
    result = send("patch", f"/api/petitions/{petition.pk}/visibility/", {"is_hidden": True}, actors["admin"])
    assert result.status_code == 200
    assert result.json()["status"] == "expired"
    assert result.json()["is_hidden"] is True
