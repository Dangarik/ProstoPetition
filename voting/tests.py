from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

class LegacyImportTests(TransactionTestCase):
    def test_import_preserves_petition_vote_and_answer(self):
        old_target = [("voting", "0001_initial")]
        executor = MigrationExecutor(connection)
        executor.migrate(old_target)
        historical = executor.loader.project_state([("users", "0007_petition_answear")]).apps
        OldPetition = historical.get_model("users", "Petition")
        OldSignature = historical.get_model("users", "PetitionSignature")
        user = get_user_model().objects.create_user(username="olduser", password="StrongPass!123")
        old = OldPetition.objects.create(
            title="Стара петиція", text="Старий текст", author_id=user.id,
            category="Освіта", status="InQue", answear="Стара відповідь",
        )
        signature = OldSignature.objects.create(petition_id=old.id, user_id=user.id)
        old_time = timezone.now() - timedelta(days=4)
        OldSignature.objects.filter(pk=signature.pk).update(timestamp=old_time)
        executor = MigrationExecutor(connection)
        executor.migrate([("voting", "0002_import_legacy")])
        from petitions.models import Petition, Response
        from voting.models import Vote
        imported = Petition.objects.get(pk=old.id)
        self.assertEqual(imported.status, "answered")
        self.assertEqual(imported.category.name, "Освіта")
        self.assertEqual(Response.objects.get(petition=imported).text, "Стара відповідь")
        vote = Vote.objects.get(petition=imported, user=user)
        self.assertLess(abs((vote.created_at - old_time).total_seconds()), 1)


