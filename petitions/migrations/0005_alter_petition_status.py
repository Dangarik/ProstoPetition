from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('petitions', '0004_remove_petition_petition_vote_threshold_positive_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='petition',
            name='status',
            field=models.CharField(choices=[('moderation', 'На модерації'), ('rejected', 'Відхилена'), ('active', 'Активна'), ('hidden', 'Прихована'), ('in_review', 'На розгляді'), ('answered', 'З відповіддю'), ('closed', 'Закрита'), ('expired', 'Термін дії минув')], db_index=True, default='moderation', max_length=20),
        ),
    ]
