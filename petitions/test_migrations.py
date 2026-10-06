from datetime import timedelta
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class RemoveHiddenMigrationTests(TransactionTestCase):
    def test_hidden_returns_to_moderation_without_losing_data(self):
        old_target = [("petitions", "0005_alter_petition_status"), ("voting", "0002_import_legacy")]
        executor = MigrationExecutor(connection)
        executor.migrate(old_target)
        apps = executor.loader.project_state(old_target).apps
        User = apps.get_model("auth", "User")
        Category = apps.get_model("petitions", "Category")
        Petition = apps.get_model("petitions", "Petition")
        Vote = apps.get_model("voting", "Vote")
        Response = apps.get_model("petitions", "Response")
        user = User.objects.create(username="legacy", is_staff=True)
        category = Category.objects.create(name="Освіта", vote_threshold=2)
        hidden = Petition.objects.create(
            title="Прихована петиція", text="Важливий текст", author=user, category=category,
            status="hidden", deadline=timezone.now() - timedelta(days=1),
            moderation_reason="Причина приховування",
        )
        vote = Vote.objects.create(petition=hidden, user=user)
        answered = Petition.objects.create(
            title="З відповіддю", text="Текст", author=user, category=category,
            status="answered", deadline=timezone.now() - timedelta(days=1),
        )
        response = Response.objects.create(petition=answered, author=user, text="Офіційна відповідь")
        try:
            executor = MigrationExecutor(connection)
            executor.migrate([("petitions", "0007_petition_is_hidden")])
            from petitions.models import Petition as CurrentPetition, Response as CurrentResponse
            from voting.models import Vote as CurrentVote
            migrated = CurrentPetition.objects.get(pk=hidden.pk)
            self.assertEqual(migrated.status, "moderation")
            self.assertNotIn(migrated.status, CurrentPetition.PUBLIC_STATUSES)
            self.assertEqual(migrated.text, "Важливий текст")
            self.assertEqual(migrated.moderation_reason, "Причина приховування")
            self.assertEqual(migrated.deadline, hidden.deadline)
            self.assertTrue(CurrentVote.objects.filter(pk=vote.pk, petition_id=hidden.pk).exists())
            self.assertEqual(CurrentPetition.objects.get(pk=answered.pk).status, "answered")
            self.assertEqual(CurrentResponse.objects.get(pk=response.pk).text, "Офіційна відповідь")
            self.assertEqual(CurrentPetition.objects.count(), 2)
            self.assertFalse(CurrentPetition.objects.filter(status="hidden").exists())
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
