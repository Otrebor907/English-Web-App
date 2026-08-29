from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import Lezione, Progresso, QuesitoFinale, QuesitoGuidato, StrutturaLezione, StrutturaQuiz, User


def _valida_password(password, utente, campo=None):
    """Esegue AUTH_PASSWORD_VALIDATORS e converte l'errore nel formato DRF.

    Necessario perché `set_password()` e `create_user()` NON eseguono i
    validatori: Django li applica solo tramite i form. Senza questa chiamata
    esplicita, AUTH_PASSWORD_VALIDATORS resterebbe una lista decorativa.

    `campo` aggancia l'errore a quel nome invece che a `non_field_errors`,
    così il client può evidenziare l'input giusto.
    """
    try:
        validate_password(password, utente)
    except DjangoValidationError as errore:
        messaggi = list(errore.messages)
        raise serializers.ValidationError({campo: messaggi} if campo else messaggi)


# Serializer usato dalla view `register` (learning/views.py): converte il JSON
# in arrivo dal form di registrazione (frontend/src/App.jsx, AuthPage) in un
# oggetto User, validando i dati PRIMA di toccare il database.
class RegisterSerializer(serializers.ModelSerializer):
    # write_only: la password si accetta in input ma non verrà mai restituita
    # nelle risposte JSON (mai esporre password, nemmeno hashate).
    password = serializers.CharField(write_only=True, min_length=8)
    # Il frontend (Auth.jsx) invia "nome"/"cognome": senza questi alias i campi
    # non combaciano con first_name/last_name e verrebbero ignorati, salvando
    # l'utente senza nome. source= li mappa sui campi reali del model.
    nome = serializers.CharField(source="first_name")
    cognome = serializers.CharField(source="last_name")

    class Meta:
        model = User
        fields = ["id", "email", "nome", "cognome", "password"]

    # Normalizza l'email (spazi + maiuscole) così "Mario@Test.com " e
    # "mario@test.com" sono trattate come la stessa identità.
    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        # UserAttributeSimilarityValidator confronta la password con gli
        # attributi dell'utente: serve un'istanza, qui non ancora salvata.
        _valida_password(attrs["password"], User(email=attrs.get("email", "")), campo="password")
        return attrs

    # Chiamato da serializer.save() nella view: NON usa User.objects.create()
    # ma create_user(), che si occupa di hashare la password (mai salvata in chiaro).
    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


# Serializer usato dalla view `login`: a differenza di RegisterSerializer non
# eredita da un model (non crea/aggiorna nulla), serve solo a validare
# l'input e a produrre l'utente autenticato in attrs["user"].
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate_email(self, value):
        return value.strip().lower()
    # Qui avviene il vero controllo delle credenziali: authenticate() è la
    # funzione standard di Django, configurata (AUTH_USER_MODEL = learning.User,
    # USERNAME_FIELD = "email" in learning/models.py) per cercare l'utente per
    # email e verificarne la password con l'hash salvato nel database.
    def validate(self, attrs):
        user = authenticate(email=attrs["email"], password=attrs["password"])
        # authenticate() ritorna None sia se l'email non esiste sia se la
        # password è sbagliata: il messaggio resta volutamente generico, per
        # non rivelare a un attaccante quale dei due campi era corretto.
        if not user:
            raise serializers.ValidationError("Email o password non validi")
        # L'utente autenticato viene passato alla view tramite validated_data,
        # che in views.login legge con serializer.validated_data["user"].
        attrs["user"] = user
        return attrs


# Forma "pubblica" dell'utente: usata per costruire il campo "utente" nella
# risposta di login/registrazione. Nota come "password" non compaia tra i
# fields: questi dati arrivano al frontend e finiscono in localStorage,
# quindi non devono MAI contenere segreti.
class UserSerializer(serializers.ModelSerializer):
    nome = serializers.CharField(source="first_name")
    cognome = serializers.CharField(source="last_name")

    class Meta:
        model = User
        fields = ["id", "email", "nome", "cognome", "creato_il", "is_staff"]


class ProfileUpdateSerializer(serializers.ModelSerializer):
    nome = serializers.CharField(source="first_name", required=False)
    cognome = serializers.CharField(source="last_name", required=False)

    class Meta:
        model = User
        fields = ["email", "nome", "cognome"]

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.exclude(pk=self.instance.pk).filter(email=value).exists():
            raise serializers.ValidationError("Questa email è già in uso.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    password_attuale = serializers.CharField(write_only=True)
    nuova_password = serializers.CharField(write_only=True, min_length=8)

    def validate_password_attuale(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Password attuale non corretta.")
        return value

    def validate_nuova_password(self, value):
        _valida_password(value, self.context["request"].user)
        return value


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrutturaLezione
        fields = ["ordine", "tipo_sezione", "contenuto", "formato_web"]


# `risposta_corretta` e `spiegazione` restano fuori dai fields: sono la
# soluzione e non devono raggiungere il client prima della verifica.
class GuidedQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuesitoGuidato
        fields = ["id", "ordine", "tipo", "testo", "opzioni"]


class FinalQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuesitoFinale
        fields = ["id", "ordine", "tipo", "testo", "opzioni"]


class QuizSerializer(serializers.ModelSerializer):
    """Espone i quesiti sotto la chiave `quesiti` qualunque sia la tabella di
    provenienza: il contratto API verso il frontend resta invariato."""
    quesiti = serializers.SerializerMethodField()

    class Meta:
        model = StrutturaQuiz
        fields = ["id", "modalita", "titolo", "quesiti"]

    def get_quesiti(self, obj):
        if obj.modalita == StrutturaQuiz.GUIDATO:
            return GuidedQuestionSerializer(obj.quesiti_guidati.all(), many=True).data
        return FinalQuestionSerializer(obj.quesiti_finali.all(), many=True).data


class LessonDetailSerializer(serializers.ModelSerializer):
    area = serializers.CharField(source="area.code")
    tipologia = serializers.CharField(source="tipologia.nome")
    livello = serializers.CharField(source="livello.code")
    difficolta = serializers.CharField(source="difficolta.code")
    sezioni = SectionSerializer(many=True, read_only=True)
    quiz = QuizSerializer(many=True, read_only=True)

    class Meta:
        model = Lezione
        fields = [
            "id", "area", "tipologia", "nome", "descrizione", "categoria", "livello", "difficolta",
            "ordine_percorso", "ordine_mvp", "obiettivo_didattico", "competenze", "durata_min",
            "errori_tipici", "sezioni", "quiz",
        ]


class ProgressSerializer(serializers.ModelSerializer):
    lezione_id = serializers.CharField()
    lezione_nome = serializers.CharField(source="lezione.nome", read_only=True)

    class Meta:
        model = Progresso
        fields = ["lezione_id", "lezione_nome", "stato", "punteggio", "completata_il", "assegnata"]
