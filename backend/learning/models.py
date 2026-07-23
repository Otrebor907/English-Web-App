from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class CodeLabel(models.Model):
    code = models.CharField(max_length=40, primary_key=True)
    nome = models.CharField(max_length=100)

    class Meta:
        abstract = True
        ordering = ["code"]

    def __str__(self):
        return self.nome


class Area(CodeLabel):
    pass


class Tipologia(CodeLabel):
    pass


class Livello(CodeLabel):
    pass


class Difficolta(CodeLabel):
    pass


class StatoLezione(CodeLabel):
    pass


class Importanza(CodeLabel):
    pass


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email è obbligatoria")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    creato_il = models.DateTimeField(auto_now_add=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()


class Lezione(models.Model):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    PRIORITA = [
        (P0, "MVP Essenziale"),
        (P1, "MVP Consigliata"),
        (P2, "MVP Secondaria"),
        (P3, "Post-MVP"),
    ]

    id = models.CharField(max_length=32, primary_key=True)
    area = models.ForeignKey(Area, on_delete=models.PROTECT)
    tipologia = models.ForeignKey(Tipologia, on_delete=models.PROTECT)
    nome = models.CharField(max_length=200)
    descrizione = models.TextField(blank=True)
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
    priorita = models.CharField(max_length=2, choices=PRIORITA, default=P3)
    ordine_mvp = models.PositiveIntegerField(null=True, blank=True, unique=True)
    importanza_mvp = models.ForeignKey(Importanza, null=True, blank=True, on_delete=models.PROTECT)
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


class SezioneLezione(models.Model):
    lezione = models.ForeignKey(Lezione, on_delete=models.CASCADE, related_name="sezioni")
    ordine = models.PositiveSmallIntegerField()
    tipo_sezione = models.CharField(max_length=80)
    contenuto = models.JSONField(default=dict)
    formato_web = models.CharField(max_length=40, default="testo")

    class Meta:
        ordering = ["ordine"]
        constraints = [models.UniqueConstraint(fields=["lezione", "ordine"], name="ordine_sezione_unico")]


class Quiz(models.Model):
    GUIDATO = "guidato"
    FINALE = "finale"
    MODALITA = [(GUIDATO, "Esercizio guidato"), (FINALE, "Quiz finale")]
    lezione = models.ForeignKey(Lezione, on_delete=models.CASCADE, related_name="quiz")
    modalita = models.CharField(max_length=10, choices=MODALITA)
    titolo = models.CharField(max_length=160)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["lezione", "modalita"], name="quiz_modalita_unica")]


class Quesito(models.Model):
    SCELTA_MULTIPLA = "scelta_multipla"
    COMPLETAMENTO = "completamento"
    TIPI = [(SCELTA_MULTIPLA, "Scelta multipla"), (COMPLETAMENTO, "Completamento")]
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="quesiti")
    ordine = models.PositiveSmallIntegerField()
    tipo = models.CharField(max_length=20, choices=TIPI)
    testo = models.TextField()
    opzioni = models.JSONField(default=list, blank=True)
    risposta_corretta = models.CharField(max_length=300)
    spiegazione = models.TextField()

    class Meta:
        ordering = ["ordine"]
        constraints = [models.UniqueConstraint(fields=["quiz", "ordine"], name="ordine_quesito_unico")]


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
