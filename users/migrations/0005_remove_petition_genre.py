
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_petition_signatures_petition_status'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='petition',
            name='genre',
        ),
    ]
