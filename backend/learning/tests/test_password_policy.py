"""Policy password, header antiframe e guardiano di configurazione (T1 / ENG-16).

Nota progettuale: i validatori Django NON vengono eseguiti da `set_password()`
né da `create_user()`. Sono pensati per i form. Valorizzare
`AUTH_PASSWORD_VALIDATORS` senza invocarli esplicitamente nei serializer
non produrrebbe alcun effetto: questi test lo verificano.
"""
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from learning.models import User


class RegistrazionePolicyPasswordTests(APITestCase):
    URL = "/api/auth/registrati/"

    def test_password_comune_respinta(self):
        risposta = self.client.post(
            self.URL,
            {"email": "tizio@example.com", "nome": "Tizio", "cognome": "Rossi", "password": "password123"},
            format="json",
        )
        self.assertEqual(risposta.status_code, 400)
        self.assertIn("password", risposta.data)
        self.assertFalse(User.objects.filter(email="tizio@example.com").exists())

    def test_password_solo_numerica_respinta(self):
        risposta = self.client.post(
            self.URL,
            {"email": "caio@example.com", "nome": "Caio", "cognome": "Bianchi", "password": "83947261"},
            format="json",
        )
        self.assertEqual(risposta.status_code, 400)
        self.assertFalse(User.objects.filter(email="caio@example.com").exists())

    def test_password_simile_alla_email_respinta(self):
        risposta = self.client.post(
            self.URL,
            {
                "email": "supermariobros@example.com",
                "nome": "Super",
                "cognome": "Mario",
                "password": "supermariobros",
            },
            format="json",
        )
        self.assertEqual(risposta.status_code, 400)
        self.assertFalse(User.objects.filter(email="supermariobros@example.com").exists())

    def test_password_troppo_corta_respinta(self):
        """Copertura preesistente: min_length=8 sul serializer."""
        risposta = self.client.post(
            self.URL,
            {"email": "breve@example.com", "nome": "Breve", "cognome": "Corti", "password": "Ab1!"},
            format="json",
        )
        self.assertEqual(risposta.status_code, 400)

    def test_password_robusta_accettata(self):
        risposta = self.client.post(
            self.URL,
            {"email": "valido@example.com", "nome": "Valido", "cognome": "Verdi", "password": "Frittata8Verde!"},
            format="json",
        )
        self.assertEqual(risposta.status_code, 201)
        self.assertTrue(User.objects.filter(email="valido@example.com").exists())


class CambioPasswordPolicyTests(APITestCase):
    """Senza questi controlli si potrebbe registrarsi con una password robusta
    e poi degradarla subito a una comune, annullando la policy."""

    URL = "/api/auth/password/"

    def setUp(self):
        self.utente = User.objects.create_user(
            email="utente@example.com", password="Frittata8Verde!"
        )
        # Autenticazione a token: è il meccanismo in vigore finché non viene
        # eseguito T3 (ENG-18). Questi due setUp andranno aggiornati in T5.
        chiave = Token.objects.create(user=self.utente).key
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {chiave}")

    def test_nuova_password_comune_respinta(self):
        risposta = self.client.post(
            self.URL,
            {"password_attuale": "Frittata8Verde!", "nuova_password": "password123"},
            format="json",
        )
        self.assertEqual(risposta.status_code, 400)
        self.utente.refresh_from_db()
        self.assertTrue(self.utente.check_password("Frittata8Verde!"))

    def test_nuova_password_robusta_accettata(self):
        risposta = self.client.post(
            self.URL,
            {"password_attuale": "Frittata8Verde!", "nuova_password": "Zucchina4Blu?"},
            format="json",
        )
        self.assertEqual(risposta.status_code, 200)
        self.utente.refresh_from_db()
        self.assertTrue(self.utente.check_password("Zucchina4Blu?"))


class HeaderAntiframeTests(APITestCase):
    def test_header_x_frame_options_presente(self):
        risposta = self.client.get("/api/lezioni/indice/")
        self.assertIn("X-Frame-Options", risposta.headers)


class GuardianoConfigurazioneTests(SimpleTestCase):
    """Il guardiano è estratto in funzione proprio per essere collaudabile:
    le impostazioni vengono valutate all'import del modulo."""

    def test_produzione_con_chiave_segnaposto_solleva(self):
        from config.settings import verifica_configurazione_produzione

        with self.assertRaises(ImproperlyConfigured):
            verifica_configurazione_produzione(debug=False, secret_key="dev-only-change-me")

    def test_produzione_con_chiave_reale_passa(self):
        from config.settings import verifica_configurazione_produzione

        verifica_configurazione_produzione(debug=False, secret_key="chiave-lunga-e-casuale-x9f2")

    def test_sviluppo_con_chiave_segnaposto_passa(self):
        from config.settings import verifica_configurazione_produzione

        verifica_configurazione_produzione(debug=True, secret_key="dev-only-change-me")
