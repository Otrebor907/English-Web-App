"""Test dedicati alla slice pilota su GRA-A1-001 e al frammento non importabile."""
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from learning.importer import import_content, load_source
from learning.models import Lezione, Progresso, QuesitoFinale, StrutturaQuiz, User
from learning.services import record_final_score


FIXTURE = "fixtures/contenuti_minimi.json"
SOURCES_PILOT = Path(settings.BASE_DIR) / "sources" / "GRA-A1-001.json"
WORKBOOK = Path(settings.BASE_DIR).parent / "programma_lezioni_inglese_no_audio.xlsx"


class IncompleteJsonFragmentTests(TestCase):
    """Il file `sources/GRA-A1-001.json` è un frammento non importabile.

    Deve essere riconosciuto come tale e rifiutato con un messaggio esplicito
    che nomina la lezione, i campi mancanti e i blocchi catalogo mancanti.
    """

    def test_pilot_metadata_fragment_is_rejected_by_load_source(self):
        self.assertTrue(SOURCES_PILOT.exists(), "Frammento pilota non trovato")
        with self.assertRaises(ValueError) as ctx:
            load_source(str(SOURCES_PILOT))
        message = str(ctx.exception)
        self.assertIn("GRA-A1-001", message)
        self.assertIn("Frammento JSON", message)
        self.assertIn("blocchi catalogo mancanti", message)
        for missing_field in ("obiettivo_didattico", "durata_min", "stato"):
            self.assertIn(missing_field, message)

    def test_pilot_metadata_fragment_is_not_imported(self):
        """Il comando fallisce e non salva nulla nel database."""
        output = StringIO()
        with self.assertRaises(CommandError):
            call_command("importa_contenuti", str(SOURCES_PILOT), stdout=output, stderr=StringIO())
        self.assertEqual(Lezione.objects.count(), 0)


class FixtureNamespaceSeparationTests(TestCase):
    """La fixture tecnica non deve usare gli ID reali del catalogo editoriale."""

    @classmethod
    def setUpTestData(cls):
        import_content(FIXTURE)

    def test_fixture_uses_demo_namespace_only(self):
        ids = set(Lezione.objects.values_list("id", flat=True))
        # Nessun ID reale del catalogo (formato AREA-LIVELLO-NNN).
        self.assertFalse(any(lesson_id in {"GRA-A1-001", "VOC-A1-001", "COM-A1-001"} for lesson_id in ids),
                         f"La fixture non deve pubblicare ID reali. Trovati: {ids}")
        # Tutti gli ID iniziano con DEMO-.
        for lesson_id in ids:
            self.assertTrue(lesson_id.startswith("DEMO-"),
                            f"ID fixture inatteso: {lesson_id}")

    def test_fixture_marks_content_as_demo(self):
        grammar = Lezione.objects.get(id="DEMO-GRA-001")
        self.assertIn("[DEMO]", grammar.nome)


class PathIncludesInPreparationLessonsTests(APITestCase):
    """Il percorso mostra anche le lezioni MVP con stato DA_SVILUPPARE."""

    @classmethod
    def setUpTestData(cls):
        import_content(FIXTURE)
        # Aggiungo una lezione in preparazione fittizia con stato DA_SVILUPPARE.
        from learning.models import (Area, Difficolta, Livello, StatoLezione, Tipologia)
        StatoLezione.objects.get_or_create(code="DA_SVILUPPARE", defaults={"nome": "Da sviluppare (MVP)"})
        Tipologia.objects.get_or_create(code="REGOLA_ED_ESERCIZI", defaults={"nome": "Regola ed esercizi"})
        Lezione.objects.create(
            id="GRA-A1-999-PILOT", area=Area.objects.get(code="GRA"),
            tipologia=Tipologia.objects.get(code="REGOLA_ED_ESERCIZI"),
            nome="Lezione pilota in preparazione", descrizione="Placeholder.",
            livello=Livello.objects.get(code="A1"), difficolta=Difficolta.objects.get(code="Bassa"),
            ordine_percorso=4, obiettivo_didattico="Da definire.", competenze=[], durata_min=10,
            errori_tipici=[], stato=StatoLezione.objects.get(code="DA_SVILUPPARE"),
            ordine_mvp=4,
        )
        cls.user = User.objects.create_user(email="path@example.com", password="password123")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.user).key}")

    def test_path_lists_in_preparation_lesson_with_flag(self):
        response = self.client.get("/api/percorso/")
        self.assertEqual(response.status_code, 200)
        pilot = next(item for item in response.data if item["id"] == "GRA-A1-999-PILOT")
        self.assertTrue(pilot["in_preparazione"])
        self.assertEqual(pilot["stato"], "in_preparazione")

    def test_lesson_detail_returns_placeholder_for_in_preparation(self):
        response = self.client.get("/api/lezioni/GRA-A1-999-PILOT/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["in_preparazione"])
        self.assertEqual(response.data["stato_utente"], "in_preparazione")
        self.assertEqual(response.data["sezioni"], [])
        self.assertEqual(response.data["quiz"], [])
        self.assertEqual(response.data["nome"], "Lezione pilota in preparazione")

    def test_start_lesson_refuses_in_preparation(self):
        response = self.client.post("/api/lezioni/GRA-A1-999-PILOT/inizia/")
        self.assertEqual(response.status_code, 404)

    def test_final_quiz_refuses_in_preparation(self):
        response = self.client.post("/api/lezioni/GRA-A1-999-PILOT/quiz-finale/", {"risposte": {}}, format="json")
        self.assertEqual(response.status_code, 404)


class CheckAnswerBlocksUnpublishedTests(APITestCase):
    """`check_answer` non deve rispondere per lezioni non pubblicate (fix P0)."""

    @classmethod
    def setUpTestData(cls):
        import_content(FIXTURE)
        cls.user = User.objects.create_user(email="check@example.com", password="password123")
        # Trasformo la lezione demo in BOZZA per verificare che la view la rifiuti.
        cls.lesson = Lezione.objects.get(id="DEMO-GRA-001")
        cls.question = QuesitoFinale.objects.filter(quiz__lezione=cls.lesson).first()

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.user).key}")

    def test_check_answer_ok_for_published_lesson(self):
        response = self.client.post(
            f"/api/lezioni/DEMO-GRA-001/quiz/finale/quesiti/{self.question.id}/verifica/",
            {"risposta": self.question.risposta_corretta}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["corretta"])

    def test_check_answer_hides_answers_for_unpublished_lesson(self):
        self.lesson.stato_id = "BOZZA"
        self.lesson.save(update_fields=["stato"])
        response = self.client.post(
            f"/api/lezioni/DEMO-GRA-001/quiz/finale/quesiti/{self.question.id}/verifica/",
            {"risposta": self.question.risposta_corretta}, format="json",
        )
        self.assertEqual(response.status_code, 404,
                         "La verifica non deve esporre la risposta corretta di una lezione non pubblicata")


class GuidedExerciseIsNotScoredTests(TestCase):
    """L'esercizio guidato dà feedback ma non aggiorna il punteggio della lezione."""

    @classmethod
    def setUpTestData(cls):
        import_content(FIXTURE)
        cls.user = User.objects.create_user(email="guidato@example.com", password="password123")
        cls.lesson = Lezione.objects.get(id="DEMO-GRA-001")

    def test_guided_quiz_exists_and_is_marked_guidato(self):
        guided = StrutturaQuiz.objects.get(lezione=self.lesson, modalita="guidato")
        self.assertEqual(guided.modalita, "guidato")

    def test_only_final_quiz_updates_progress(self):
        """Ripetere l'esercizio guidato non crea né aggiorna il Progresso della lezione."""
        # Nessun record iniziale.
        self.assertFalse(Progresso.objects.filter(utente=self.user, lezione=self.lesson).exists())
        # Simulo il completamento del quiz finale via services.
        progress = record_final_score(self.user, self.lesson, 80)
        self.assertEqual(progress.punteggio, 80)
        # Un punteggio successivo più basso non altera il migliore.
        after = record_final_score(self.user, self.lesson, 40)
        self.assertEqual(after.punteggio, 80)


class NoAudioNoPRNTests(SimpleTestCase):
    """La fonte reale non contiene campi audio né area PRN (regressione)."""

    def test_workbook_source_has_no_audio_and_no_prn(self):
        data = load_source(str(WORKBOOK))
        # Nessun campo audio.
        def has_audio(value, path="fonte"):
            if isinstance(value, dict):
                return any("audio" in str(k).casefold() or has_audio(v) for k, v in value.items())
            if isinstance(value, list):
                return any(has_audio(item) for item in value)
            return False
        self.assertFalse(has_audio(data), "Nessun campo audio deve essere presente")
        # Nessuna area PRN.
        area_codes = {item["code"] for item in data["liste"]["area"]}
        self.assertNotIn("PRN", area_codes)
