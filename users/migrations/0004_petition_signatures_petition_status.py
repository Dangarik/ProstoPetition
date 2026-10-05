
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='petition',
            name='signatures',
            field=models.IntegerField(blank=True, default=0),
        ),
        migrations.AddField(
            model_name='petition',
            name='status',
            field=models.CharField(choices=[('Started', 'Збір підписів'), ('InQue', 'В черзі на відповідь'), ('Done', 'З відповіддю')], default='Збір підписів', max_length=100),
        ),
    ]
