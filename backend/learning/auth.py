"""Sostituti delle parti di django.contrib.auth che il progetto usava davvero.

Quell'app e' stata disinstallata insieme al pannello /admin/ (vedi il commento
in config/settings.py). Restava pero' un pezzo indispensabile: DRF, davanti a
una richiesta senza credenziali, mette in request.user un oggetto "utente
anonimo", e per impostazione predefinita usa quello di django.contrib.auth.
Qui c'e' il rimpiazzo, agganciato da REST_FRAMEWORK["UNAUTHENTICATED_USER"],
insieme alla classe che legge il token di sessione dalla nostra tabella.
"""

from rest_framework.authentication import TokenAuthentication as TokenAuthDRF

from .models import Token


class TokenAuthentication(TokenAuthDRF):
    """Identica a quella di DRF, ma legge da user_authtoken_token.

    DRF cerca il token nel proprio modello (tabella authtoken_token) a meno che
    non gli si indichi il modello da usare: e' l'aggancio previsto per i token
    personalizzati. Vedi learning.models.Token.
    """

    model = Token


class AnonymousUser:
    """Il visitatore non autenticato.

    Espone solo cio' che il codice interroga davvero: is_authenticated per
    distinguere il visitatore dall'utente (views.lesson_index, lesson_detail),
    is_staff per IsAdminUser, is_active per completezza. Non tocca il database:
    non e' un record, e' l'assenza di un record.
    """

    id = None
    pk = None
    is_active = False
    is_staff = False
    is_superuser = False
    is_authenticated = False
    is_anonymous = True

    def __str__(self):
        return "Anonimo"

    def __eq__(self, other):
        return isinstance(other, AnonymousUser)

    def __hash__(self):
        return hash(AnonymousUser)
