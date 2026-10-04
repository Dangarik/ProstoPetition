from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.name

class Petition(models.Model):
    class Status(models.TextChoices):
        MODERATION = "moderation", "На модерації"
        REJECTED = "rejected", "Відхилена"
        ACTIVE = "active", "Активна"
        HIDDEN = "hidden", "Прихована"
        IN_REVIEW = "in_review", "На розгляді"
        ANSWERED = "answered", "З відповіддю"
        CLOSED = "closed", "Закрита"

    PUBLIC_STATUSES = (Status.ACTIVE, Status.IN_REVIEW, Status.ANSWERED, Status.CLOSED)
    title = models.CharField(max_length=255)
    text = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="petitions")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="petitions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.MODERATION, db_index=True)
    deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    status_changed_at = models.DateTimeField(default=timezone.now)
    moderation_reason = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "-created_at"])]

    def is_active(self):
        return self.status == self.Status.ACTIVE and self.deadline > timezone.now()

    def __str__(self):
        return self.title

class Response(models.Model):
    petition = models.OneToOneField(Petition, on_delete=models.CASCADE, related_name="official_response")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                               help_text="NULL лише для імпортованих старих відповідей без даних про автора.")
    text = models.TextField()
    published_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.petition_id and self.petition.status != Petition.Status.IN_REVIEW:
            raise ValidationError("Відповідь можлива лише для петиції на розгляді.")
        if self.author_id and not self.author.is_staff:
            raise ValidationError("Відповідь може опублікувати лише адміністратор.")

