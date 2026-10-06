from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import APIException
from petitions.models import Petition
from petitions.services import expire_petitions
from .models import Vote

class VoteConflict(APIException):
    status_code = 409
    default_detail = "Голос уже подано або петиція не приймає голоси."

def cast_vote(petition_id, user):
    try:
        with transaction.atomic():
            petition = Petition.objects.select_for_update().get(pk=petition_id)
            now = timezone.now()
            if expire_petitions(Petition.objects.filter(pk=petition_id), now=now):
                petition.status = Petition.Status.EXPIRED
            if petition.status != Petition.Status.EXPIRED:
                if (petition.status != Petition.Status.ACTIVE or petition.deadline <= now
                        or petition.category.vote_threshold is None
                        or Vote.objects.filter(user=user, petition=petition).exists()):
                    raise VoteConflict()
                vote = Vote.objects.create(user=user, petition=petition)
                count = Vote.objects.filter(petition=petition).count()
                threshold = petition.category.vote_threshold
                if threshold is not None and count >= threshold:
                    petition.status = Petition.Status.IN_REVIEW
                    petition.status_changed_at = timezone.now()
                    petition.save(update_fields=["status", "status_changed_at"])
                return vote, count, petition.status, petition.is_active()
        raise VoteConflict("Термін збору голосів завершено.")
    except IntegrityError:
        raise VoteConflict()

