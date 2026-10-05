
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_petitionsignature'),
    ]

    operations = [
        migrations.AddField(
            model_name='petition',
            name='answear',
            field=models.TextField(blank=True, null=True),
        ),
    ]
