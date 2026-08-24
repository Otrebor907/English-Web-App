from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MaxValueValidator, MinValueValidator
import re

from django.db import models


class CodeLabel(models.Model):
    code = models.CharField(max_length=40, primary_key=True)
    nome = models.CharField(max_length=100)

    class Meta:
        abstract = True
        ordering = ["code"]

    def __str__(self):
        return self.nome


# Tabelle di mapping: associano un codice stabile a un'etichetta leggibile.
# db_table esplicita perche' il nome non segue piu' la convenzione <app>_<model>.
class Area(CodeLabel):
    class Meta(CodeLabel.Meta):
        db_table = "mapping_area_lezione"


class Tipologia(CodeLabel):
    class Meta(CodeLabel.Meta):
        db_table = "mapping_tipologia"


class Livello(CodeLabel):
    class Meta(CodeLabel.Meta):
        db_table = "mapping_livello"


class Difficolta(CodeLabel):
    class Meta(CodeLabel.Meta):
        db_table = "mapping_difficolta_lezione"


class StatoLezione(CodeLabel):
    pass


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


# Utente custom di questo progetto: eredita da AbstractUser (che include già
# password, is_staff, is_superuser, ecc.) ma sostituisce il login-by-username
# di Django con login-by-email, coerente col form di AuthPage (solo email + password).
class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    creato_il = models.DateTimeField(auto_now_add=True)
    # Dice a Django (e quindi ad authenticate() usato in LoginSerializer.validate)
    # di usare "email" come identificativo di accesso al posto di "username".
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()


# Deriva l'ID della lezione immediatamente precedente nella stessa serie:
# prende le ultime cifre dell'ID, le decrementa e ricompone il codice con lo
# stesso padding. Restituisce None quando la serie e' al primo elemento.
# ATTENZIONE: e' un suggerimento, non il grafo dei prerequisiti (vedi Prerequisito).
ID_SERIE = re.compile(r"^(?P<prefisso>.*?)(?P<numero>\d+)$")


def id_lezione_precedente(lesson_id):
    match = ID_SERIE.match(str(lesson_id or ""))
    if not match:
        return None
    numero = int(match.group("numero"))
    if numero <= 1:
        return None
    larghezza = len(match.group("numero"))
    return f"{match.group('prefisso')}{numero - 1:0{larghezza}d}"


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
    fase_roadmap = models.CharField(max_length=80)
    prerequisiti = models.ManyToManyField("self", through="Prerequisito", symmetrical=False, related_name="sblocca")

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

    @property
    def prerequisito_derivato(self):
        """ID della lezione precedente nella serie, derivato dal codice.
        Suggerimento di navigazione: i prerequisiti reali sono in `prerequisiti`."""
        return id_lezione_precedente(self.id)

    def __str__(self):
        return f"{self.id} — {self.nome}"


class Prerequisito(models.Model):
    lezione = models.ForeignKey(Lezione, on_delete=models.CASCADE, related_name="vincoli")
    richiede_lezione = models.ForeignKey(Lezione, on_delete=models.PROTECT, related_name="richiesta_da")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["lezione", "richiede_lezione"], name="prerequisito_unico"),
            models.CheckConstraint(condition=~models.Q(lezione=models.F("richiede_lezione")), name="no_auto_prerequisito"),
        ]


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
    minuti_effettivi = models.PositiveIntegerField(default=0)
    assegnata = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["utente", "lezione"], name="progresso_unico")]
