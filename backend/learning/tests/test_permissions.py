"""Verifica i permessi a livello di route/API: consultazione libera, scrittura solo autenticata."""
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase
from learning.importer import import_content
from learning.models import Progresso, QuesitoFinale, QuesitoGuidato, User


FIXTURE = "fixtures/contenuti_minimi.json"


class AnonymousReadAccessTests(APITestCase):
    """Un visitatore non autenticato può leggere l'indice e il contenuto di ogni lezione."""

    @classmethod
    def setUpTestData(cls):
        import_content(FIXTURE)

    def setUp(self):
        self.client = APIClient()  # nessuna credenziale: richiesta anonima

    def test_anonymous_can_read_lesson_index(self):
        response = self.client.get("/api/lezioni/indice/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("GRA", response.data)
        grammar_ids = [item["id"] for item in response.data["GRA"]]
        self.assertIn("DEMO-GRA-001", grammar_ids)
        first = next(item for item in response.data["GRA"] if item["id"] == "DEMO-GRA-001")
        self.assertIsNone(first["stato"])
        self.assertFalse(first["assegnata"])

    def test_anonymous_can_read_full_lesson_content_without_answers(self):
        response = self.client.get("/api/lezioni/DEMO-GRA-001/")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.data["sezioni"]), 0)
        self.assertGreater(len(response.data["quiz"]), 0)
        self.assertIsNone(response.data["stato_utente"])
        self.assertFalse(response.data["assegnata"])
        self.assertFalse(response.data["autenticato"])
        # Nessuna risposta corretta esposta a un visitatore
        for quiz in response.data["quiz"]:
            for question in quiz["quesiti"]:
                self.assertNotIn("risposta_corretta", question)
                self.assertNotIn("spiegazione", question)


class AnonymousWriteBlockedTests(APITestCase):
    """Ogni azione di scrittura resta bloccata lato server, non solo nascosta lato UI."""

    @classmethod
    def setUpTestData(cls):
        import_content(FIXTURE)

    def setUp(self):
        self.client = APIClient()

    def test_anonymous_cannot_assign_lesson(self):
        response = self.client.post("/api/lezioni/DEMO-GRA-001/assegna/")
        self.assertEqual(response.status_code, 401)
        self.assertFalse(Progresso.objects.filter(lezione_id="DEMO-GRA-001").exists())

    def test_anonymous_cannot_start_lesson(self):
        response = self.client.post("/api/lezioni/DEMO-GRA-001/inizia/")
        self.assertEqual(response.status_code, 401)

    def test_anonymous_cannot_check_answer(self):
        question = QuesitoGuidato.objects.filter(quiz__lezione_id="DEMO-GRA-001").first()
        response = self.client.post(f"/api/lezioni/DEMO-GRA-001/quiz/guidato/quesiti/{question.id}/verifica/", {"risposta": "x"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_anonymous_cannot_submit_final_quiz(self):
        response = self.client.post("/api/lezioni/DEMO-GRA-001/quiz-finale/", {"risposte": {}}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_anonymous_cannot_read_progress_page(self):
        response = self.client.get("/api/progressi/")
        self.assertEqual(response.status_code, 401)


class AuthenticatedAssignmentTests(APITestCase):
    """Un utente autenticato assegna/rimuove liberamente le lezioni; il punteggio resta salvato."""

    @classmethod
    def setUpTestData(cls):
        import_content(FIXTURE)
        cls.user = User.objects.create_user(email="assign@example.com", password="password123")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.user).key}")

    def test_assign_and_unassign_lesson(self):
        assign = self.client.post("/api/lezioni/DEMO-VOC-001/assegna/")
        self.assertEqual(assign.status_code, 200)
        self.assertTrue(assign.data["assegnata"])

        progress_page = self.client.get("/api/progressi/")
        self.assertEqual([item["lezione_id"] for item in progress_page.data], ["DEMO-VOC-001"])

        remove = self.client.delete("/api/lezioni/DEMO-VOC-001/assegna/")
        self.assertEqual(remove.status_code, 200)
        self.assertFalse(remove.data["assegnata"])

        progress_page = self.client.get("/api/progressi/")
        self.assertEqual(progress_page.data, [])

    def test_progress_list_is_empty_when_nothing_assigned(self):
        response = self.client.get("/api/progressi/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_can_exercise_a_lesson_without_assigning_it_first(self):
        lesson_id = "DEMO-GRA-001"
        self.assertFalse(Progresso.objects.filter(utente=self.user, lezione_id=lesson_id, assegnata=True).exists())
        questions = QuesitoFinale.objects.filter(quiz__lezione_id=lesson_id)
        answers = {str(question.id): question.risposta_corretta for question in questions}
        result = self.client.post(f"/api/lezioni/{lesson_id}/quiz-finale/", {"risposte": answers}, format="json")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["punteggio"], 100)

    def test_completing_final_quiz_auto_assigns_the_lesson(self):
        lesson_id = "DEMO-GRA-001"
        questions = QuesitoFinale.objects.filter(quiz__lezione_id=lesson_id)
        answers = {str(question.id): question.risposta_corretta for question in questions}
        self.client.post(f"/api/lezioni/{lesson_id}/quiz-finale/", {"risposte": answers}, format="json")
        progress = Progresso.objects.get(utente=self.user, lezione_id=lesson_id)
        self.assertTrue(progress.assegnata)
