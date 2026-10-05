from datetime import timedelta
from django.db import migrations
from django.utils import timezone

def readable(value):
    if not value:
        return ""
    try:
        return value.encode("cp1251").decode("utf-8")
    except (UnicodeError, ValueError):
        return value

def forwards(apps, schema_editor):
    OldPetition = apps.get_model("users", "Petition")
    OldSignature = apps.get_model("users", "PetitionSignature")
    Category = apps.get_model("petitions", "Category")
    Petition = apps.get_model("petitions", "Petition")
    Response = apps.get_model("petitions", "Response")
    Vote = apps.get_model("voting", "Vote")
    db = schema_editor.connection.alias
    now = timezone.now()

    for old in OldPetition.objects.using(db).all().iterator():
        name = readable(old.category).strip() or "Без теми"
        category, _ = Category.objects.using(db).get_or_create(name=name[:100])
        answer = (old.answear or "").strip()
        if answer:
            state = "answered"
        elif old.status == "InQue":
            state = "in_review"
        elif old.status == "Done":
            state = "closed"
        else:
            state = "active"
        deadline = now + timedelta(days=30) if state == "active" else old.time_create + timedelta(days=30)
        Petition.objects.using(db).create(
            id=old.id, title=old.title, text=old.text or "(Текст не збережено)",
            author_id=old.author_id, category_id=category.id,
            status=state, deadline=deadline, status_changed_at=now,
        )
        Petition.objects.using(db).filter(id=old.id).update(created_at=old.time_create)
        if answer:
            Response.objects.using(db).create(
                petition_id=old.id, author_id=None, text=answer,
            )
        for signature in OldSignature.objects.using(db).filter(petition_id=old.id).iterator():
            vote, created = Vote.objects.using(db).get_or_create(
                petition_id=old.id, user_id=signature.user_id,
            )
            if created:
                Vote.objects.using(db).filter(pk=vote.pk).update(created_at=signature.timestamp)

class Migration(migrations.Migration):
    dependencies = [
        ("users", "0007_petition_answear"),
        ("petitions", "0002_alter_response_author"),
        ("voting", "0001_initial"),
    ]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]


