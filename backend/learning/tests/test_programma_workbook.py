from copy import deepcopy
from pathlib import Path
from django.conf import settings
from django.test import SimpleTestCase, TestCase
from learning.importer import import_content, load_source, validate_source
from learning.models import Lezione, Quiz, SezioneLezione


PROGRAMMA = Path(settings.BASE_DIR).parent / "programma_lezioni_inglese_no_audio.xlsx"


class ProgrammaWorkbookTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not PROGRAMMA.exists():
            raise AssertionError(f"File sorgente obbligatorio non trovato: {PROGRAMMA}")
        cls.data = load_source(PROGRAMMA)

    def test_native_workbook_is_mapped_without_inventing_content(self):
        self.assertEqual(len(self.data["lezioni"]), 98)
        self.assertEqual(sum(row["ordine_mvp"] is not None for row in self.data["lezioni"]), 29)
        self.assertEqual(len(self.data["sezioni"]), 824)
        self.assertEqual(self.data["quiz"], [])
        self.assertTrue(all(section["contenuto"]["todo"].startswith("TODO_FONTE:") for section in self.data["sezioni"]))

    def test_gra_a1_008_is_included_and_real_source_dag_passes(self):
        lessons = {row["id"]: row for row in self.data["lezioni"]}
        self.assertEqual(lessons["GRA-A1-008"]["ordine_mvp"], 11)
        self.assertEqual(lessons["GRA-A1-008"]["priorita"], "P1")
        self.assertEqual(lessons["GRA-A1-009"]["ordine_mvp"], 12)
        validate_source(self.data)

    def test_catalog_has_only_supported_areas_and_priorities(self):
        self.assertEqual({row["area"] for row in self.data["lezioni"]}, {"GRA", "VOC", "COM"})
        self.assertEqual({row["priorita"] for row in self.data["lezioni"]}, {"P0", "P1", "P2", "P3"})
        self.assertEqual(
            [row["ordine_percorso"] for row in self.data["lezioni"]],
            list(range(1, 99)),
        )

    def test_audio_fields_are_rejected(self):
        data = deepcopy(self.data)
        data["lezioni"][0]["audio_url"] = "https://example.invalid/audio.mp3"
        with self.assertRaisesRegex(ValueError, "Campi audio non ammessi"):
            validate_source(data)

    def test_prn_lookup_is_rejected(self):
        data = deepcopy(self.data)
        data["liste"]["area"].append({"code": "PRN", "nome": "Pronuncia"})
        with self.assertRaisesRegex(ValueError, "esclusivamente GRA, VOC e COM"):
            validate_source(data)

    def test_priority_must_match_mvp_importance(self):
        data = deepcopy(self.data)
        next(row for row in data["lezioni"] if row["id"] == "GRA-A1-008")["priorita"] = "P0"
        with self.assertRaisesRegex(ValueError, "incoerente con importanza_mvp"):
            validate_source(data)


class ProgrammaWorkbookImportTests(TestCase):
    def test_real_workbook_import_is_idempotent(self):
        first = import_content(PROGRAMMA)
        second = import_content(PROGRAMMA)

        self.assertEqual(first, {"lezioni": 98, "prerequisiti": 119})
        self.assertEqual(second, first)
        self.assertEqual(Lezione.objects.count(), 98)
        self.assertEqual(Lezione.objects.filter(ordine_mvp__isnull=False).count(), 29)
        self.assertEqual(Lezione.objects.get(id="GRA-A1-008").priorita, "P1")
        self.assertEqual(SezioneLezione.objects.count(), 824)
        self.assertEqual(Quiz.objects.count(), 0)
