from django.db import migrations, models
from django.utils import timezone


def return_hidden_to_moderation(apps, schema_editor):
    Petition = apps.get_model("petitions", "Petition")
    Petition.objects.using(schema_editor.connection.alias).filter(status="hidden").update(
        status="moderation", status_changed_at=timezone.now(),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('petitions', '0005_alter_petition_status'),
    ]

    operations = [
        migrations.RunPython(return_hidden_to_moderation, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='petition',
            name='status',
            field=models.CharField(choices=[('moderation', 'На модерації'), ('rejected', 'Відхилена'), ('active', 'Активна'), ('in_review', 'На розгляді'), ('answered', 'З відповіддю'), ('closed', 'Закрита'), ('expired', 'Термін дії минув')], db_index=True, default='moderation', max_length=20),
        ),
    ]
