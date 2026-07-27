from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import Lezione, Progresso, Quesito, Quiz, SezioneLezione, User


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


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "email", "password"]

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        # UserAttributeSimilarityValidator confronta la password con gli
        # attributi dell'utente: serve un'istanza, qui non ancora salvata.
        _valida_password(attrs["password"], User(email=attrs.get("email", "")), campo="password")
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        user = authenticate(email=attrs["email"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Email o password non validi")
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "creato_il", "is_staff"]


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email"]

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
        model = SezioneLezione
        fields = ["ordine", "tipo_sezione", "contenuto", "formato_web"]


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quesito
        fields = ["id", "ordine", "tipo", "testo", "opzioni"]


class QuizSerializer(serializers.ModelSerializer):
    quesiti = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ["id", "modalita", "titolo", "quesiti"]


class LessonDetailSerializer(serializers.ModelSerializer):
    area = serializers.CharField(source="area.code")
    tipologia = serializers.CharField(source="tipologia.nome")
    livello = serializers.CharField(source="livello.code")
    difficolta = serializers.CharField(source="difficolta.code")
    importanza_mvp = serializers.CharField(source="importanza_mvp.code", allow_null=True)
    sezioni = SectionSerializer(many=True, read_only=True)
    quiz = QuizSerializer(many=True, read_only=True)

    class Meta:
        model = Lezione
        fields = [
            "id", "area", "tipologia", "nome", "descrizione", "categoria", "livello", "difficolta",
            "ordine_percorso", "priorita", "ordine_mvp", "obiettivo_didattico", "competenze", "durata_min",
            "errori_tipici", "importanza_mvp", "fase_roadmap", "sezioni", "quiz",
        ]


class ProgressSerializer(serializers.ModelSerializer):
    lezione_id = serializers.CharField()
    lezione_nome = serializers.CharField(source="lezione.nome", read_only=True)

    class Meta:
        model = Progresso
        fields = ["lezione_id", "lezione_nome", "stato", "punteggio", "completata_il", "minuti_effettivi", "assegnata"]
