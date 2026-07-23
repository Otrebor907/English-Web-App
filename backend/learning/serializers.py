from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import Lezione, Progresso, Quesito, Quiz, SezioneLezione, User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "email", "password"]

    def validate_email(self, value):
        return value.strip().lower()

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
