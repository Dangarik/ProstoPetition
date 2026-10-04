from django.db import models
from django.contrib.auth.models import User

class Petition(models.Model):
    title = models.CharField(max_length=255)
    text = models.TextField(blank=True)
    time_create = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=100,
        choices=[
            ('Started', 'Збір підписів'),
            ('InQue', 'В черзі на відповідь'),
            ('Done', 'З відповіддю'),
        ],
        default='Збір підписів'
    )
    signatures = models.IntegerField(blank=True, default=0)
    category = models.CharField(
        max_length=100,
        choices=[
            ('Без теми', 'Без теми'),
            ('Економіка', 'Економіка'),
            ('Грамадська діяльність', 'Грамадська діяльність'),
            ('Освіта', 'Освіта'),
            ('Наука', 'Наука'),
        ],
        default='Без теми'
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prosto_petition_set')
    answear = models.TextField(blank=True, null=True)  # Поле для відповіді

    def save(self, *args, **kwargs):
        if self.answear:
            self.status = 'З відповіддю'
        super().save(*args, **kwargs)


    def __str__(self):
        return self.title

class PetitionSignature(models.Model):
    petition = models.ForeignKey(Petition, on_delete=models.CASCADE, related_name='signatures_list')  # Петиція
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Користувач, який підписав
    timestamp = models.DateTimeField(auto_now_add=True)  # Час підпису

    class Meta:
        unique_together = ('petition', 'user')