
import django.core.validators
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('petitions', '0002_alter_response_author'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='max_days',
            field=models.PositiveSmallIntegerField(default=0, validators=[django.core.validators.MaxValueValidator(366)]),
        ),
        migrations.AddField(
            model_name='category',
            name='max_months',
            field=models.PositiveSmallIntegerField(default=0, validators=[django.core.validators.MaxValueValidator(11)]),
        ),
        migrations.AddField(
            model_name='category',
            name='max_years',
            field=models.PositiveSmallIntegerField(default=1, validators=[django.core.validators.MaxValueValidator(100)]),
        ),
        migrations.AddField(
            model_name='petition',
            name='vote_threshold',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name='category',
            constraint=models.CheckConstraint(condition=models.Q(('max_years__gte', 0), ('max_months__gte', 0), ('max_days__gte', 0), models.Q(('max_years__gt', 0), ('max_months__gt', 0), ('max_days__gt', 0), _connector='OR')), name='category_duration_positive'),
        ),
        migrations.AddConstraint(
            model_name='petition',
            constraint=models.CheckConstraint(condition=models.Q(('vote_threshold__isnull', True), ('vote_threshold__gte', 1), _connector='OR'), name='petition_vote_threshold_positive'),
        ),
    ]
