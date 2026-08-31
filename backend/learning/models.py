from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from rest_framework.authtoken.models import Token as TokenDRF


class CodeLabel(models.Model):
    code = models.CharField(max_length=40, primary_key=True)
    nome = models.CharField(max_length=100)

    class Meta:
        abstract = True
        ordering = ["code"]

    def __str__(self):
        return self.nome


# Tabelle dimensione (dim_*): associano un codice stabile a un'etichetta leggibile.
# db_table esplicita perche' il nome non segue piu' la convenzione <app>_<model>.
# Minuscolo di proposito: Postgres abbassa gli identificatori non virgolettati,
# quindi "SELECT * FROM dim_livello" funziona senza virgolette.
class Area(CodeLabel):
    class Meta(CodeLabel.Meta):
        db_table = "dim_area_lezione"


class Tipologia(CodeLabel):
    class Meta(CodeLabel.Meta):
        db_table = "dim_tipologia"


class Livello(CodeLabel):
    class Meta(CodeLabel.Meta):
        db_table = "dim_livello"


class Difficolta(CodeLabel):
    class Meta(CodeLabel.Meta):
        db_table = "dim_difficolta_lezione"


class StatoLezione(CodeLabel):
    class Meta(CodeLabel.Meta):
        db_table = "dim_stato_lezione"


# Django, di default, crea utenti con create_user(username, password). Qui invece
# l'app non ha username: bisogna dire esplicitamente a Django come creare un
# utente a partire da email+password (usato da RegisterSerializer.create()).
class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email è obbligatoria")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        # set_password() applica l'hashing (mai la password in chiaro nel DB):
        # è ciò che rende verificabile la password al login senza salvarla in chiaro.
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


# Utente custom di questo progetto: eredita da AbstractBaseUser (password +
# last_login + hashing) e NON da AbstractUser, che porterebbe con se'
# PermissionsMixin e i permessi granulari di Django. Qui non servono: l'unica
# distinzione e' "utente normale" vs "amministratore", e la fa is_staff.
class User(AbstractBaseUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    # is_active: usato da authenticate() per bloccare gli account disattivati.
    is_active = models.BooleanField(default=True)
    # is_staff: e' cio' che IsAdminUser controlla sulle rotte riservate (es.
    # /api/contenuti/gaps/). Unico livello di privilegio effettivo del progetto.
    is_staff = models.BooleanField(default=False)
    # is_superuser: marca l'account proprietario. Nessun codice lo interroga da
    # quando /admin/ non esiste piu'; resta come etichetta.
    is_superuser = models.BooleanField(default=False)
    creato_il = models.DateTimeField(auto_now_add=True)
    # Dice a Django (e quindi ad authenticate() usato in LoginSerializer.validate)
    # di usare "email" come identificativo di accesso al posto di "username".
    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        db_table = "user_profile"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name


# Il token di sessione dell'API. DRF ne fornisce uno pronto, ma nella tabella
# authtoken_token: fuori dallo schema di nomi del progetto. La sua classe
# diventa astratta quando "rest_framework.authtoken" non e' in INSTALLED_APPS
# (e' un aggancio previsto da DRF), quindi qui la si eredita cambiando solo il
# nome della tabella. Campi e comportamento restano quelli di DRF: chiave
# generata da os.urandom, una sola riga per utente.
# Chi lo legge a ogni richiesta e' learning.auth.TokenAuthentication.
class Token(TokenDRF):
    class Meta:
        db_table = "user_authtoken_token"


class Lezione(models.Model):
    id = models.CharField(max_length=32, primary_key=True)
    area = models.ForeignKey(Area, on_delete=models.PROTECT)
    tipologia = models.ForeignKey(Tipologia, on_delete=models.PROTECT)
    nome = models.CharField(max_length=200)
    descrizione = models.TextField(blank=True)
    categoria = models.CharField(max_length=120, blank=True, default="")
    livello = models.ForeignKey(Livello, on_delete=models.PROTECT)
    difficolta = models.ForeignKey(Difficolta, on_delete=models.PROTECT)
    ordine_percorso = models.PositiveIntegerField(
        unique=True,
        validators=[MinValueValidator(1), MaxValueValidator(98)],
    )
    obiettivo_didattico = models.TextField()
    competenze = models.JSONField(default=list)
    durata_min = models.PositiveSmallIntegerField()
    errori_tipici = models.JSONField(default=list)
    stato = models.ForeignKey(StatoLezione, on_delete=models.PROTECT)
    ordine_mvp = models.PositiveIntegerField(null=True, blank=True, unique=True)

    class Meta:
        ordering = ["ordine_mvp", "ordine_percorso"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(area_id__in=["GRA", "VOC", "COM"]),
                name="lezione_area_supportata",
            ),
            models.CheckConstraint(
                condition=models.Q(ordine_percorso__gte=1, ordine_percorso__lte=98),
                name="ordine_percorso_1_98",
            ),
        ]

    def __str__(self):
        return f"{self.id} — {self.nome}"


class StrutturaLezione(models.Model):
    """Struttura editoriale della lezione: le sezioni ordinate che la compongono."""
    lezione = models.ForeignKey(Lezione, on_delete=models.CASCADE, related_name="sezioni")
    ordine = models.PositiveSmallIntegerField()
    tipo_sezione = models.CharField(max_length=80)
    contenuto = models.JSONField(default=dict)
    formato_web = models.CharField(max_length=40, default="testo")

    class Meta:
        db_table = "struttura_lezione"
        ordering = ["ordine"]
        constraints = [models.UniqueConstraint(fields=["lezione", "ordine"], name="ordine_sezione_unico")]


class StrutturaQuiz(models.Model):
    """Struttura della parte esercitativa finale della lezione."""
    GUIDATO = "guidato"
    FINALE = "finale"
    MODALITA = [(GUIDATO, "Esercizio guidato"), (FINALE, "Quiz finale")]
    lezione = models.ForeignKey(Lezione, on_delete=models.CASCADE, related_name="quiz")
    modalita = models.CharField(max_length=10, choices=MODALITA)
    titolo = models.CharField(max_length=160)

    class Meta:
        db_table = "struttura_quiz"
        constraints = [models.UniqueConstraint(fields=["lezione", "modalita"], name="quiz_modalita_unica")]


class QuesitoBase(models.Model):
    """Colonne condivise dai quesiti guidati e finali.

    Guidato e finale hanno struttura identica: la differenza e' il momento
    didattico, non i dati. La base astratta tiene le due tabelle allineate
    ed evita che divergano nel tempo.
    """
    SCELTA_MULTIPLA = "scelta_multipla"
    COMPLETAMENTO = "completamento"
    TIPI = [(SCELTA_MULTIPLA, "Scelta multipla"), (COMPLETAMENTO, "Completamento")]
    ordine = models.PositiveSmallIntegerField()
    tipo = models.CharField(max_length=20, choices=TIPI)
    testo = models.TextField()
    opzioni = models.JSONField(default=list, blank=True)
    risposta_corretta = models.CharField(max_length=300)
    spiegazione = models.TextField()

    class Meta:
        abstract = True
        ordering = ["ordine"]


class QuesitoGuidato(QuesitoBase):
    """Quesiti dell'esercizio guidato: correzione immediata, uno alla volta."""
    quiz = models.ForeignKey(
        StrutturaQuiz, on_delete=models.CASCADE, related_name="quesiti_guidati",
        limit_choices_to={"modalita": StrutturaQuiz.GUIDATO},
    )

    class Meta(QuesitoBase.Meta):
        abstract = False
        db_table = "struttura_quiz_guidato"
        constraints = [models.UniqueConstraint(fields=["quiz", "ordine"], name="ordine_quesito_guidato_unico")]


class QuesitoFinale(QuesitoBase):
    """Quesiti del quiz finale: corretti in blocco, producono il punteggio."""
    quiz = models.ForeignKey(
        StrutturaQuiz, on_delete=models.CASCADE, related_name="quesiti_finali",
        limit_choices_to={"modalita": StrutturaQuiz.FINALE},
    )

    class Meta(QuesitoBase.Meta):
        abstract = False
        db_table = "struttura_quiz_finale"
        constraints = [models.UniqueConstraint(fields=["quiz", "ordine"], name="ordine_quesito_finale_unico")]


class Progresso(models.Model):
    BLOCCATA = "bloccata"
    DISPONIBILE = "disponibile"
    IN_CORSO = "in_corso"
    COMPLETATA = "completata"
    STATI = [(BLOCCATA, "Bloccata"), (DISPONIBILE, "Disponibile"), (IN_CORSO, "In corso"), (COMPLETATA, "Completata")]
    utente = models.ForeignKey(User, on_delete=models.CASCADE, related_name="progressi")
    lezione = models.ForeignKey(Lezione, on_delete=models.CASCADE, related_name="progressi")
    stato = models.CharField(max_length=12, choices=STATI, default=DISPONIBILE)
    punteggio = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    completata_il = models.DateTimeField(null=True, blank=True)
    assegnata = models.BooleanField(default=False)

    class Meta:
        db_table = "user_progress"
        constraints = [models.UniqueConstraint(fields=["utente", "lezione"], name="progresso_unico")]
