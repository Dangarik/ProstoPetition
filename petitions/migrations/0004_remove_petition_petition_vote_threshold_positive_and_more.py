
from django.db import migrations, models


def copy_unambiguous_thresholds(apps, schema_editor):
    Category = apps.get_model('petitions', 'Category')
    Petition = apps.get_model('petitions', 'Petition')
    db = schema_editor.connection.alias
    for category in Category.objects.using(db).all().iterator():
        values = list(Petition.objects.using(db).filter(category_id=category.pk)
                      .exclude(vote_threshold__isnull=True)
                      .values_list('vote_threshold', flat=True).distinct()[:2])
        if len(values) == 1:
            Category.objects.using(db).filter(pk=category.pk).update(vote_threshold=values[0])


class Migration(migrations.Migration):

    dependencies = [
        ('petitions', '0003_category_max_days_category_max_months_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='vote_threshold',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.RunPython(copy_unambiguous_thresholds, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name='petition',
            name='petition_vote_threshold_positive',
        ),
        migrations.RemoveField(
            model_name='petition',
            name='vote_threshold',
        ),
        migrations.AddConstraint(
            model_name='category',
            constraint=models.CheckConstraint(condition=models.Q(('vote_threshold__isnull', True), ('vote_threshold__gte', 1), _connector='OR'), name='category_vote_threshold_positive'),
        ),
    ]
