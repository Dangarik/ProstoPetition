from datetime import datetime, timedelta, timezone as datetime_timezone
import pytest
from django.utils import timezone
from petitions.models import Petition
from petitions.services import PetitionConflict, change_status, reconcile_category_threshold
from voting.models import Vote
from voting.services import VoteConflict, cast_vote


pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("status,days,expected", [
    ("active", 1, True), ("active", -1, False), ("moderation", 1, False),
    ("expired", 1, False), ("closed", 1, False),
])
def test_is_active(status, days, expected, petition):
    petition.status = status
    petition.deadline = timezone.now() + timedelta(days=days)
    assert petition.is_active() is expected


@pytest.mark.parametrize("source,target", [
    ("moderation", "active"), ("moderation", "rejected"),
    ("active", "in_review"), ("active", "closed"),
])
def test_allowed_transition_updates_status_and_timestamp(petition, source, target):
    petition.status = source
    petition.save()
    before = timezone.now()
    change_status(petition.pk, target, reason="Порушення правил")
    petition.refresh_from_db()
    assert petition.status == target
    assert petition.status_changed_at >= before
    assert petition.moderation_reason == ("Порушення правил" if target == "rejected" else "")


@pytest.mark.parametrize("source,target", [
    ("moderation", "answered"), ("rejected", "active"), ("in_review", "active"),
    ("answered", "closed"), ("closed", "active"),
])
def test_forbidden_transition_leaves_data_unchanged(petition, source, target):
    petition.status = source
    petition.save()
    before = petition.status_changed_at
    with pytest.raises(PetitionConflict):
        change_status(petition.pk, target)
    petition.refresh_from_db()
    assert petition.status == source
    assert petition.status_changed_at == before


@pytest.mark.parametrize("status", ["expired", "closed", "rejected", "answered"])
def test_terminal_states_reject_votes(petition, actors, status):
    petition.status = status
    petition.save()
    with pytest.raises(VoteConflict):
        cast_vote(petition.pk, actors["voter"])
    assert not Vote.objects.filter(petition=petition).exists()


def test_category_calendar_duration_clamps_month_end(category):
    category.max_years, category.max_months, category.max_days = 0, 1, 2
    start = datetime(2024, 1, 31, 12, tzinfo=datetime_timezone.utc)
    assert category.maximum_deadline(start) == datetime(2024, 3, 2, 12, tzinfo=datetime_timezone.utc)


def test_activation_requires_category_threshold(petition, category):
    category.vote_threshold = None
    category.save()
    with pytest.raises(PetitionConflict):
        change_status(petition.pk, "active")
    petition.refresh_from_db()
    assert petition.status == "moderation"


def test_activation_rejects_elapsed_deadline(petition):
    petition.deadline = timezone.now() - timedelta(seconds=1)
    petition.save()
    with pytest.raises(PetitionConflict):
        change_status(petition.pk, "active")
    petition.refresh_from_db()
    assert petition.status == "moderation"


def test_activation_preserves_existing_votes_and_enters_review(petition, category, actors):
    category.vote_threshold = 1
    category.save()
    vote = Vote.objects.create(petition=petition, user=actors["voter"])
    change_status(petition.pk, "active")
    petition.refresh_from_db()
    assert petition.status == "in_review"
    assert petition.votes.get().pk == vote.pk


def test_lowered_threshold_does_not_revive_expired_petition(petition, category, actors):
    category.vote_threshold = 1
    category.save()
    petition.status = "active"
    petition.deadline = timezone.now() - timedelta(seconds=1)
    petition.save()
    Vote.objects.create(petition=petition, user=actors["voter"])
    reconcile_category_threshold(category.pk)
    petition.refresh_from_db()
    assert petition.status == "expired"
    assert petition.votes.count() == 1
