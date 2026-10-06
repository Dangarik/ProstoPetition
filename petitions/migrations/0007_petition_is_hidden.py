from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('petitions', '0006_alter_petition_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='petition',
            name='is_hidden',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
