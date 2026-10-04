from django.db import IntegrityError, transaction
from rest_framework.exceptions import APIException
from petitions.models import Petition
from .models import Vote

class VoteConflict(APIException):
    status_code = 409
    default_detail = "Голос уже подано або петиція не приймає голоси."

def cast_vote(petition_id, user):
    try:
        with transaction.atomic():
            petition = Petition.objects.select_for_update().get(pk=petition_id)
            if not petition.is_active() or Vote.objects.filter(user=user, petition=petition).exists():
                raise VoteConflict()
            vote = Vote.objects.create(user=user, petition=petition)
            count = Vote.objects.filter(petition=petition).count()
            return vote, count
    except IntegrityError:
        raise VoteConflict()

