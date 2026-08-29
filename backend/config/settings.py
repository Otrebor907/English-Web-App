import os
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
# Legge il file .env nella radice del progetto, cioè un livello sopra backend/:
# contiene le credenziali Neon e non è versionato. Deve stare prima di ogni
# os.getenv() qui sotto, altrimenti le impostazioni verrebbero valutate quando
# le variabili non esistono ancora. Le variabili già presenti nell'ambiente
# reale vincono, perché load_dotenv() non le sovrascrive: così Docker e CI
# restano padroni della propria configurazione.
load_dotenv(BASE_DIR.parent / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [host for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host]

# Niente django.contrib.admin: il pannello /admin/ e' stato rimosso, e con lui
# le app che esistevano solo per reggerlo (auth, contenttypes, sessions,
# messages) e le loro tabelle (auth_group, auth_group_permissions,
# auth_permission, django_admin_log, django_content_type, django_session).
# I contenuti si pubblicano dai comandi importa_contenuti / pubblica_da_markdown.
# CONSEGUENZA: non esistono piu' i comandi createsuperuser e changepassword,
# che arrivavano da django.contrib.auth. Per creare un amministratore:
#   python manage.py shell -c "from learning.models import User; \
#     User.objects.create_superuser(email='...', password='...')"
INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "learning",
]

# L'API si autentica col token DRF (header Authorization), non con la sessione:
# sessioni, auth e messages servivano solo all'admin. XFrameOptions resta,
# non c'entra con l'admin: protegge dal clickjacking.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"

if os.getenv("POSTGRES_DB"):
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        # --- righe nuove, necessarie per Neon ---
        "OPTIONS": {"sslmode": os.getenv("POSTGRES_SSLMODE", "require")},
        # Neon sospende il compute dopo 5 minuti di inattività (scale-to-zero,
        # non disattivabile sul piano gratuito). Senza il controllo di salute
        # Django riuserebbe una connessione ormai chiusa dal server.
        "CONN_HEALTH_CHECKS": True,
        # Il pooler di Neon (PgBouncer in transaction mode) non supporta
        # i cursori lato server.
        "DISABLE_SERVER_SIDE_CURSORS": True,
    }}

else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

# MinimumLengthValidator è volutamente assente: la lunghezza minima di 8
# è già imposta da RegisterSerializer e ChangePasswordSerializer.
# ATTENZIONE: questi validatori non vengono eseguiti da set_password().
# Sono invocati esplicitamente nei serializer di learning/serializers.py.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
]
AUTH_USER_MODEL = "learning.User"
LANGUAGE_CODE = "it-it"
TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CORS_ALLOWED_ORIGINS = [
    origin for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",") if origin
]
# TokenAuthentication: per OGNI richiesta, DRF legge l'header
#   Authorization: Token <valore>
# (impostato da frontend/src/api.js) e cerca quel token nel database per
# risalire all'utente. Se manca o non corrisponde a nessun utente,
# request.user resta anonimo.
# IsAuthenticated: regola di default per TUTTE le view — per questo login e
# register devono dichiarare esplicitamente @permission_classes([AllowAny]),
# altrimenti nessuno potrebbe mai autenticarsi la prima volta.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    # Chi non presenta un token finisce qui. Il default di DRF sarebbe
    # django.contrib.auth.models.AnonymousUser, che non e' piu' importabile
    # da quando quell'app e' stata disinstallata: vedi learning/auth.py.
    "UNAUTHENTICATED_USER": "learning.auth.AnonymousUser",
}

SECRET_KEY_SEGNAPOSTO = "dev-only-change-me"


def verifica_configurazione_produzione(debug, secret_key):
    """Impedisce l'avvio in produzione con la chiave segnaposto.

    Il rischio reale non è una configurazione sbagliata ma una dimenticata:
    senza questo controllo l'app partirebbe silenziosamente insicura.
    Estratta in funzione per poter essere collaudata: le impostazioni
    vengono valutate una sola volta, all'import del modulo.
    """
    if not debug and secret_key == SECRET_KEY_SEGNAPOSTO:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY non valorizzata mentre DEBUG è disattivato. "
            "Impostare una chiave lunga e casuale prima di avviare in produzione."
        )


verifica_configurazione_produzione(DEBUG, SECRET_KEY)
