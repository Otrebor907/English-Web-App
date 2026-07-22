from copy import deepcopy
from django.test import SimpleTestCase, TestCase
from learning.importer import load_source
from learning.models import Lezione
from learning.services import GraphValidationError, validate_lesson_graph


FIXTURE = "fixtures/contenuti_minimi.json"


class GraphValidationTests(SimpleTestCase):
    def setUp(self):
        self.data = load_source(FIXTURE)

    def test_fixture_dag_is_valid_and_all_published_lessons_are_reachable(self):
        validate_lesson_graph(self.data["lezioni"], self.data["prerequisiti"])

    def test_missing_prerequisite_fails_loudly(self):
        edges = deepcopy(self.data["prerequisiti"])
        edges.append({"lezione_id": "DEMO-COM-001", "richiede_lezione_id": "OUT-OF-SCOPE"})
        with self.assertRaisesRegex(GraphValidationError, "fuori perimetro o inesistente"):
            validate_lesson_graph(self.data["lezioni"], edges)

    def test_prerequisite_outside_mvp_fails_loudly(self):
        lessons = deepcopy(self.data["lezioni"])
        next(row for row in lessons if row["id"] == "DEMO-GRA-001")["ordine_mvp"] = None
        with self.assertRaisesRegex(GraphValidationError, "fuori perimetro MVP"):
            validate_lesson_graph(lessons, self.data["prerequisiti"])

    def test_future_prerequisite_fails_loudly(self):
        edges = [{"lezione_id": "DEMO-GRA-001", "richiede_lezione_id": "DEMO-VOC-001"}]
        with self.assertRaisesRegex(GraphValidationError, "Ordine prerequisito non valido"):
            validate_lesson_graph(self.data["lezioni"], edges)

    def test_cycle_fails_loudly(self):
        edges = deepcopy(self.data["prerequisiti"])
        edges.append({"lezione_id": "DEMO-GRA-001", "richiede_lezione_id": "DEMO-COM-001"})
        with self.assertRaisesRegex(GraphValidationError, "Ciclo nel grafo"):
            validate_lesson_graph(self.data["lezioni"], edges)

    def test_additional_root_is_unreachable_and_fails(self):
        edges = [self.data["prerequisiti"][0]]
        with self.assertRaisesRegex(GraphValidationError, "non raggiungibili"):
            validate_lesson_graph(self.data["lezioni"], edges)

    def test_published_path_cannot_cross_an_unpublished_lesson(self):
        lessons = deepcopy(self.data["lezioni"])
        next(row for row in lessons if row["id"] == "DEMO-VOC-001")["stato"] = "BOZZA"
        with self.assertRaisesRegex(GraphValidationError, "DEMO-COM-001"):
            validate_lesson_graph(lessons, self.data["prerequisiti"])


class PersistedPublishedGraphBuildTest(TestCase):
    """Build guard: the actual imported published graph must remain reachable."""

    @classmethod
    def setUpTestData(cls):
        from learning.importer import import_content
        import_content(FIXTURE)

    def test_every_published_lesson_in_database_is_reachable(self):
        lessons = [{
            "id": lesson.id, "ordine_percorso": lesson.ordine_percorso,
            "ordine_mvp": lesson.ordine_mvp, "stato": lesson.stato_id,
        } for lesson in Lezione.objects.all()]
        prerequisites = [{
            "lezione_id": edge.lezione_id, "richiede_lezione_id": edge.richiede_lezione_id,
        } for lesson in Lezione.objects.prefetch_related("vincoli") for edge in lesson.vincoli.all()]
        validate_lesson_graph(lessons, prerequisites)
