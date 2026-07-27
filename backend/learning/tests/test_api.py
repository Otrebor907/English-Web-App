from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase
from learning.importer import import_content
from learning.models import Quesito, User


class ApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        import_content("fixtures/contenuti_minimi.json")
        cls.user = User.objects.create_user(email="api@example.com", password="password123")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.user).key}")

    def test_lesson_is_available_and_lists_recommended_prerequisite(self):
        response = self.client.get("/api/percorso/")
        self.assertEqual([item["ordine_mvp"] for item in response.data], [1, 2, 3])
        self.assertEqual(response.data[0]["priorita"], "P0")
        vocabulary = next(item for item in response.data if item["id"] == "DEMO-VOC-001")
        self.assertEqual(vocabulary["stato"], "disponibile")
        self.assertEqual(vocabulary["prerequisiti_mancanti"][0]["id"], "DEMO-GRA-001")

    def test_final_quiz_is_scored_on_server(self):
        questions = Quesito.objects.filter(quiz__lezione_id="DEMO-GRA-001", quiz__modalita="finale")
        answers = {str(question.id): question.risposta_corretta for question in questions}
        response = self.client.post("/api/lezioni/DEMO-GRA-001/quiz-finale/", {"risposte": answers}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["punteggio"], 100)
        self.assertTrue(response.data["superato"])

    def test_content_gaps_requires_staff(self):
        response = self.client.get("/api/admin/contenuti-mancanti/")
        self.assertEqual(response.status_code, 403)

    def test_staff_can_read_content_gaps(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        response = self.client.get("/api/admin/contenuti-mancanti/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["riepilogo"]["lezioni_mvp"], 3)


class FullUserJourneyTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        import_content("fixtures/contenuti_minimi.json")

    def test_registration_lesson_quiz_completion_and_free_access(self):
        client = APIClient()
        registration = client.post(
            "/api/auth/registrati/",
            {"email": "journey@example.com", "password": "Frittata8Verde!"},
            format="json",
        )
        self.assertEqual(registration.status_code, 201)
        client.credentials(HTTP_AUTHORIZATION=f"Token {registration.data['token']}")

        initial_path = client.get("/api/percorso/")
        grammar = next(item for item in initial_path.data if item["id"] == "DEMO-GRA-001")
        vocabulary = next(item for item in initial_path.data if item["id"] == "DEMO-VOC-001")
        self.assertEqual(grammar["stato"], "disponibile")
        self.assertEqual(vocabulary["stato"], "disponibile")

        lesson = client.get("/api/lezioni/DEMO-GRA-001/")
        self.assertEqual(lesson.status_code, 200)
        self.assertEqual(client.post("/api/lezioni/DEMO-GRA-001/inizia/").status_code, 200)

        questions = Quesito.objects.filter(quiz__lezione_id="DEMO-GRA-001", quiz__modalita="finale")
        answers = {str(question.id): question.risposta_corretta for question in questions}
        result = client.post("/api/lezioni/DEMO-GRA-001/quiz-finale/", {"risposte": answers}, format="json")
        self.assertEqual(result.data["punteggio"], 100)
        self.assertEqual(result.data["stato"], "completata")

        after_completion = client.get("/api/percorso/")
        vocabulary = next(item for item in after_completion.data if item["id"] == "DEMO-VOC-001")
        self.assertEqual(vocabulary["stato"], "disponibile")
        progress = client.get("/api/progressi/")
        grammar_progress = next(item for item in progress.data if item["lezione_id"] == "DEMO-GRA-001")
        self.assertEqual(grammar_progress["punteggio"], 100)
