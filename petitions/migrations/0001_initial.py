
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Petition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('text', models.TextField()),
                ('status', models.CharField(choices=[('moderation', 'На модерації'), ('rejected', 'Відхилена'), ('active', 'Активна'), ('hidden', 'Прихована'), ('in_review', 'На розгляді'), ('answered', 'З відповіддю'), ('closed', 'Закрита')], db_index=True, default='moderation', max_length=20)),
                ('deadline', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('status_changed_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('moderation_reason', models.TextField(blank=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='petitions', to=settings.AUTH_USER_MODEL)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='petitions', to='petitions.category')),
            ],
        ),
        migrations.CreateModel(
            name='Response',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('published_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('petition', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='official_response', to='petitions.petition')),
            ],
        ),
        migrations.AddIndex(
            model_name='petition',
            index=models.Index(fields=['status', '-created_at'], name='petitions_p_status_c24065_idx'),
        ),
    ]
