from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from petitions.models import Petition

class Vote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="votes")
    petition = models.ForeignKey(Petition, on_delete=models.CASCADE, related_name="votes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "petition"], name="unique_user_petition_vote")]

    def clean(self):
        if not self.petition.is_active():
            raise ValidationError("Голосувати можна лише за активну петицію до дедлайну.")

