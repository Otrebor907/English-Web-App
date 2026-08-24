from django.test import TestCase
from learning.importer import import_content
from learning.models import Area, Lezione, Progresso, User
from learning.services import lesson_state, record_final_score


FIXTURE = "fixtures/contenuti_minimi.json"


class ImportAndProgressTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        import_content(FIXTURE)
        cls.user = User.objects.create_user(email="learner@example.com", password="password123")

    def test_import_is_idempotent(self):
        before = Lezione.objects.count()
        import_content(FIXTURE)
        self.assertEqual(Lezione.objects.count(), before)

    def test_fixture_has_only_three_areas_and_persists_priority(self):
        self.assertSetEqual(set(Area.objects.values_list("code", flat=True)), {"GRA", "VOC", "COM"})
        self.assertEqual(Lezione.objects.get(id="DEMO-GRA-001").ordine_mvp, 1)

    def test_lessons_are_never_locked_by_prerequisites(self):
        grammar = Lezione.objects.get(id="DEMO-GRA-001")
        vocabulary = Lezione.objects.get(id="DEMO-VOC-001")
        self.assertEqual(lesson_state(self.user, grammar), Progresso.DISPONIBILE)
        self.assertEqual(lesson_state(self.user, vocabulary), Progresso.DISPONIBILE)
        record_final_score(self.user, grammar, 75)
        self.assertEqual(lesson_state(self.user, vocabulary), Progresso.DISPONIBILE)

    def test_best_score_is_preserved_and_threshold_completes(self):
        grammar = Lezione.objects.get(id="DEMO-GRA-001")
        record_final_score(self.user, grammar, 75)
        progress = record_final_score(self.user, grammar, 50)
        self.assertEqual(progress.punteggio, 75)
        self.assertEqual(progress.stato, Progresso.COMPLETATA)
