from django.conf import settings
import calendar
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    max_years = models.PositiveSmallIntegerField(default=1, validators=[MaxValueValidator(100)])
    max_months = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(11)])
    max_days = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(366)])
    vote_threshold = models.PositiveIntegerField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(max_years__gte=0) & models.Q(max_months__gte=0) &
                           models.Q(max_days__gte=0) &
                           (models.Q(max_years__gt=0) | models.Q(max_months__gt=0) | models.Q(max_days__gt=0))),
                name="category_duration_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(vote_threshold__isnull=True) | models.Q(vote_threshold__gte=1),
                name="category_vote_threshold_positive",
            ),
        ]

    def clean(self):
        if not any((self.max_years, self.max_months, self.max_days)):
            raise ValidationError("Ліміт категорії має бути більшим за нуль.")
        if self.vote_threshold is None or self.vote_threshold < 1:
            raise ValidationError({"vote_threshold": "Вкажіть додатний поріг голосів для категорії."})

    def maximum_deadline(self, start):
        month_index = start.year * 12 + start.month - 1 + self.max_years * 12 + self.max_months
        year, month_zero = divmod(month_index, 12)
        month = month_zero + 1
        day = min(start.day, calendar.monthrange(year, month)[1])
        return start.replace(year=year, month=month, day=day) + timedelta(days=self.max_days)

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

    def clean(self):
        if self._state.adding and self.category_id and self.deadline:
            if self.deadline > self.category.maximum_deadline(timezone.now()):
                raise ValidationError({"deadline": "Дедлайн перевищує ліміт категорії."})

    def is_active(self):
        return (self.status == self.Status.ACTIVE and self.deadline > timezone.now()
                and self.category.vote_threshold is not None)

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

