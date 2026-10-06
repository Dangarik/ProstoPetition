from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException
from .models import Petition, Response

class PetitionConflict(APIException):
    status_code = 409
    default_detail = "Операція несумісна з поточним станом петиції."

TRANSITIONS = {
    Petition.Status.MODERATION: {Petition.Status.ACTIVE, Petition.Status.REJECTED},
    Petition.Status.ACTIVE: {Petition.Status.IN_REVIEW, Petition.Status.CLOSED},
}

def expire_petitions(queryset=None, now=None):
    now = now or timezone.now()
    queryset = Petition.objects.all() if queryset is None else queryset
    return queryset.filter(status=Petition.Status.ACTIVE, deadline__lte=now).update(
        status=Petition.Status.EXPIRED, status_changed_at=now,
    )


def change_status(petition_id, new_status, reason=""):
    with transaction.atomic():
        petition = Petition.objects.select_for_update().get(pk=petition_id)
        now = timezone.now()
        if expire_petitions(Petition.objects.filter(pk=petition_id), now=now):
            petition.status = Petition.Status.EXPIRED
        if petition.status != Petition.Status.EXPIRED:
            if new_status not in TRANSITIONS.get(petition.status, set()):
                raise PetitionConflict("Недозволений перехід стану.")
            if new_status == Petition.Status.ACTIVE and petition.category.vote_threshold is None:
                raise PetitionConflict("Спочатку вкажіть поріг голосів для категорії.")
            if new_status == Petition.Status.REJECTED and not reason.strip():
                raise PetitionConflict("Причина відхилення є обов’язковою.")
            if new_status == Petition.Status.ACTIVE and petition.deadline <= now:
                raise PetitionConflict("Термін петиції вже завершився.")
            if new_status == Petition.Status.ACTIVE and petition.votes.count() >= petition.category.vote_threshold:
                new_status = Petition.Status.IN_REVIEW
            petition.status = new_status
            petition.moderation_reason = reason.strip() if new_status == Petition.Status.REJECTED else ""
            petition.status_changed_at = now
            petition.save(update_fields=["status", "moderation_reason", "status_changed_at"])
            return petition
    raise PetitionConflict("Термін збору голосів завершено.")

def reconcile_category_threshold(category_id):
    ids = list(Petition.objects.filter(category_id=category_id, status=Petition.Status.ACTIVE).values_list("pk", flat=True))
    for petition_id in ids:
        with transaction.atomic():
            petition = Petition.objects.select_for_update().get(pk=petition_id)
            if expire_petitions(Petition.objects.filter(pk=petition_id)):
                continue
            threshold = petition.category.vote_threshold
            if petition.status == Petition.Status.ACTIVE and threshold is not None and petition.votes.count() >= threshold:
                petition.status = Petition.Status.IN_REVIEW
                petition.status_changed_at = timezone.now()
                petition.save(update_fields=["status", "status_changed_at"])

def publish_response(petition_id, author, text):
    with transaction.atomic():
        petition = Petition.objects.select_for_update().get(pk=petition_id)
        if petition.status != Petition.Status.IN_REVIEW or Response.objects.filter(petition=petition).exists():
            raise PetitionConflict("Відповідь можлива лише один раз для петиції на розгляді.")
        response = Response.objects.create(petition=petition, author=author, text=text)
        petition.status = Petition.Status.ANSWERED
        petition.status_changed_at = timezone.now()
        petition.save(update_fields=["status", "status_changed_at"])
        return response

