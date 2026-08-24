from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase
from learning.importer import import_content
from learning.models import QuesitoFinale, User


class ApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        import_content("fixtures/contenuti_minimi.json")
        cls.user = User.objects.create_user(email="api@example.com", password="password123")

    def setUp(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.user).key}")

    def test_lesson_is_available_and_lists_recommended_prerequisite(self):
        response = self.client.get("/api/percorso/")
        print(response.data)
        self.assertEqual([item["ordine_mvp"] for item in response.data], [1, 2, 3])
        self.assertEqual(response.data[0]["ordine_mvp"], 1)
        vocabulary = next(item for item in response.data if item["id"] == "DEMO-VOC-001")
        self.assertEqual(vocabulary["stato"], "disponibile")
        self.assertEqual(vocabulary["prerequisiti_mancanti"][0]["id"], "DEMO-GRA-001")

    def test_final_quiz_is_scored_on_server(self):
        questions = QuesitoFinale.objects.filter(quiz__lezione_id="DEMO-GRA-001")
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


# Test "di percorso" (end-to-end): invece di collaudare un singolo endpoint,
# ripercorre l'INTERO viaggio di un utente reale — iscrizione, apertura della
# lezione, quiz, progressi salvati — nell'ordine in cui accade davvero.
# Il valore aggiunto sta proprio nella sequenza: verifica che i pezzi, ognuno
# già collaudato singolarmente altrove, funzionino anche INSIEME.
class FullUserJourneyTests(APITestCase):
    # setUpTestData prepara la scena UNA SOLA VOLTA per tutta la classe (a
    # differenza di setUp, che rigirerebbe prima di ogni singolo test): qui
    # carica le 3 lezioni finte di fixtures/contenuti_minimi.json nel database
    # di prova, che Django crea e distrugge da solo ad ogni esecuzione.
    # Il database vero (db.sqlite3) non viene mai toccato.
    @classmethod
    def setUpTestData(cls):
        import_content("fixtures/contenuti_minimi.json")

    def test_registration_lesson_quiz_completion_and_free_access(self):
        # APIClient è un browser finto: manda richieste HTTP all'app senza che
        # serva un server acceso. Qui ne serve uno nuovo e "vergine" perché
        # l'utente del viaggio deve partire da anonimo, senza token.
        client = APIClient()
        # TAPPA 1 — Registrazione. Stessa chiamata che fa il form di Auth.jsx
        # quando premi "Crea account".
        registration = client.post(
            "/api/auth/registrati/",
            {"email": "journey@example.com", "nome": "Journey", "cognome": "User", "password": "Frittata8Verde!"},
            format="json",
        )
        # 201 = "Created": l'utente ora esiste nel database.
        self.assertEqual(registration.status_code, 201)
        # La registrazione restituisce un token. Da qui in poi il client lo
        # allega ad ogni richiesta nell'header Authorization: è l'equivalente
        # del token che il frontend salva in localStorage (vedi api.js).
        # Senza questa riga tutte le chiamate successive risponderebbero 401.
        client.credentials(HTTP_AUTHORIZATION=f"Token {registration.data['token']}")

        # TAPPA 2 — Il percorso appena iscritti: cosa vede l'utente all'inizio.
        initial_path = client.get("/api/percorso/")
        # next(... if ...) pesca dalla lista la lezione con quell'id: le due
        # lezioni finte caricate da setUpTestData.
        grammar = next(item for item in initial_path.data if item["id"] == "DEMO-GRA-001")
        vocabulary = next(item for item in initial_path.data if item["id"] == "DEMO-VOC-001")
        # Il cuore della scelta di prodotto: NESSUNA lezione è bloccata. Anche
        # VOC-001, che ha GRA-001 come prerequisito, resta "disponibile" —
        # i prerequisiti sono un consiglio, non un cancello.
        self.assertEqual(grammar["stato"], "disponibile")
        self.assertEqual(vocabulary["stato"], "disponibile")

        # TAPPA 3 — L'utente apre la lezione e preme "inizia".
        lesson = client.get("/api/lezioni/DEMO-GRA-001/")
        self.assertEqual(lesson.status_code, 200)
        # 200 anche qui: l'avvio viene registrato (la lezione passa "in corso").
        self.assertEqual(client.post("/api/lezioni/DEMO-GRA-001/inizia/").status_code, 200)

        # TAPPA 4 — Il quiz finale, risposto perfettamente.
        # Il test si legge dal database le risposte giuste (risposta_corretta
        # arriva dalla fixture) e costruisce { id_del_quesito: risposta_giusta }.
        # Così simula uno studente che non sbaglia nulla, e può pretendere 100.
        questions = QuesitoFinale.objects.filter(quiz__lezione_id="DEMO-GRA-001")
        answers = {str(question.id): question.risposta_corretta for question in questions}
        result = client.post("/api/lezioni/DEMO-GRA-001/quiz-finale/", {"risposte": answers}, format="json")
        # Il punteggio lo calcola il SERVER, non il browser: è la difesa contro
        # un utente che provi a dichiararsi 100 modificando la richiesta.
        self.assertEqual(result.data["punteggio"], 100)
        self.assertEqual(result.data["stato"], "completata")

        # TAPPA 5 — Il controllo finale: l'effetto è stato salvato DAVVERO?
        # Non basta che la risposta del quiz dicesse 100: queste chiamate
        # rileggono da zero e verificano che il 100 sia rimasto nel database.
        after_completion = client.get("/api/percorso/")
        vocabulary = next(item for item in after_completion.data if item["id"] == "DEMO-VOC-001")
        # Ricontrollata DOPO il completamento: conferma che il prerequisito
        # soddisfatto non abbia cambiato nulla, perché era già accessibile.
        self.assertEqual(vocabulary["stato"], "disponibile")
        progress = client.get("/api/progressi/")
        grammar_progress = next(item for item in progress.data if item["lezione_id"] == "DEMO-GRA-001")
        self.assertEqual(grammar_progress["punteggio"], 100)
