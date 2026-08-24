from collections import defaultdict
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import Lezione, Progresso, QuesitoFinale, QuesitoGuidato, StrutturaQuiz
from .serializers import (
    ChangePasswordSerializer, LessonDetailSerializer, LoginSerializer, ProfileUpdateSerializer,
    ProgressSerializer, RegisterSerializer, UserSerializer,
)
from .services import (
    assign_lesson, assigned_lesson_ids, completed_lesson_ids, lesson_state, mark_in_progress,
    missing_prerequisites, record_final_score, sync_progress, unassign_lesson,
)


def _correct_variants(question):
    """Risposte accettate. Per il completamento sono ammesse più varianti separate da « | »
    (es. forma piena e contratta di una traduzione)."""
    return [variant.strip() for variant in question.risposta_corretta.split("|") if variant.strip()]


def _answer_matches(question, answer):
    if answer is None:
        return False
    if question.tipo == question.COMPLETAMENTO:
        given = str(answer).strip().casefold()
        return any(given == variant.casefold() for variant in _correct_variants(question))
    return str(answer) == question.risposta_corretta


def _display_answer(question):
    """Risposta corretta leggibile: le varianti « | » diventano « / »."""
    return " / ".join(_correct_variants(question)) or question.risposta_corretta


# @permission_classes([AllowAny]) sovrascrive la regola globale IsAuthenticated
# impostata in config/settings.py (REST_FRAMEWORK): serve perché per registrarsi
# non si può ancora possedere un token di autenticazione.
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def register(request):
    # request.data è il JSON inviato dal frontend: { email, password }.
    # RegisterSerializer (learning/serializers.py) valida formato email e
    # robustezza password (AUTH_PASSWORD_VALIDATORS di Django) prima di procedere.
    serializer = RegisterSerializer(data=request.data)
    # raise_exception=True: se i dati non sono validi, solleva automaticamente
    # un errore HTTP 400 con i messaggi di validazione — è così che il frontend
    # riceve err.data.password nel catch di AuthPage.submit.
    serializer.is_valid(raise_exception=True)
    # .save() chiama RegisterSerializer.create(), che crea l'utente nel database
    # con la password già hashata (User.objects.create_user -> set_password).
    user = serializer.save()
    # Crea (o riusa) il token DRF associato al nuovo utente: è la stringa che
    # il frontend salverà in localStorage e userà per le richieste future.
    token, _ = Token.objects.get_or_create(user=user)
    # 201 Created + { token, utente }: esattamente il payload che AuthPage passa
    # ad authenticate() per "accendere" lo stato di login nel frontend.
    return Response({"token": token.key, "utente": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


# Stesso ragionamento di register: login deve essere accessibile anche senza token.
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def login(request):
    # LoginSerializer non crea nulla: valida email/password e, dentro il suo
    # metodo validate(), chiama authenticate(email=..., password=...) — la
    # funzione di Django che verifica le credenziali contro il database.
    serializer = LoginSerializer(data=request.data)
    # Se authenticate() non trova un utente con quella email/password,
    # LoginSerializer solleva ValidationError("Email o password non validi")
    # e questa riga la trasforma in una risposta 400 al client.
    serializer.is_valid(raise_exception=True)
    # Se siamo arrivati qui, le credenziali sono corrette: recuperiamo l'utente
    # che il serializer ha attaccato ad attrs["user"] durante la validazione.
    user = serializer.validated_data["user"]
    # get_or_create: se l'utente ha già un token da un login precedente lo riusa,
    # altrimenti ne crea uno nuovo. Un solo token attivo per utente alla volta.
    token, _ = Token.objects.get_or_create(user=user)
    # Risposta 200 con { token, utente }: qui finisce, lato server, il "flusso di
    # accesso" — da qui in poi ogni richiesta autenticata del frontend porterà
    # questo stesso token nell'header Authorization (vedi frontend/src/api.js).
    return Response({"token": token.key, "utente": UserSerializer(user).data})


@api_view(["GET", "PATCH"])
def profile(request):
    if request.method == "PATCH":
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    return Response(UserSerializer(request.user).data)


@api_view(["POST"])
def change_password(request):
    serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    request.user.set_password(serializer.validated_data["nuova_password"])
    request.user.save(update_fields=["password"])
    Token.objects.filter(user=request.user).delete()
    token = Token.objects.create(user=request.user)
    return Response({"token": token.key})


STATO_IN_PREPARAZIONE = "in_preparazione"
# Ogni stato editoriale è esposto: chi non è "PUBBLICATA" appare come "in preparazione".
STATI_LEZIONE_ESPOSTI = ["PUBBLICATA", "DA_SVILUPPARE", "DA_SVILUPPARE_MVP", "IN_SVILUPPO", "IN_REVISIONE", "COMPLETATA"]


def _lesson_summary_payload(lesson, user, completed):
    """Riepilogo comune per una card lezione nel percorso."""
    base = {
        "id": lesson.id, "nome": lesson.nome, "descrizione": lesson.descrizione,
        "area": lesson.area_id, "categoria": lesson.categoria,
        "livello": lesson.livello_id, "durata_min": lesson.durata_min,
        "ordine_mvp": lesson.ordine_mvp,
    }
    if lesson.stato_id != "PUBBLICATA":
        return {**base, "stato": STATO_IN_PREPARAZIONE, "in_preparazione": True,
                "punteggio": 0, "prerequisiti_mancanti": []}
    missing = missing_prerequisites(user, lesson, completed)
    progress = Progresso.objects.filter(utente=user, lezione=lesson).first()
    return {**base, "stato": lesson_state(user, lesson),
            "in_preparazione": False,
            "punteggio": progress.punteggio if progress else 0,
            "prerequisiti_mancanti": [{"id": item.id, "nome": item.nome} for item in missing]}


@api_view(["GET"])
def path_lessons(request):
    sync_progress(request.user)
    lessons = Lezione.objects.filter(
        ordine_mvp__isnull=False, stato_id__in=STATI_LEZIONE_ESPOSTI,
    ).select_related("area", "livello", "difficolta").prefetch_related("prerequisiti").order_by("ordine_mvp")
    completed = completed_lesson_ids(request.user)
    return Response([_lesson_summary_payload(lesson, request.user, completed) for lesson in lessons])


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def lesson_index(request):
    """Indice completo delle lezioni per area — pubblico, nessun filtro MVP, nessun blocco.
    Stato e assegnazione sono informazioni personali: presenti solo per chi ha effettuato l'accesso."""
    user = request.user if request.user.is_authenticated else None
    assigned = assigned_lesson_ids(user) if user else set()
    lessons = Lezione.objects.select_related("area", "livello").order_by("area_id", "ordine_percorso")
    by_area = defaultdict(list)
    for lesson in lessons:
        in_prep = lesson.stato_id != "PUBBLICATA"
        by_area[lesson.area_id].append({
            "id": lesson.id, "nome": lesson.nome, "descrizione": lesson.descrizione,
            "categoria": lesson.categoria,
            "livello": lesson.livello_id, "durata_min": lesson.durata_min,
            "ordine_percorso": lesson.ordine_percorso, "in_preparazione": in_prep,
            "stato": None if not user else ("in_preparazione" if in_prep else lesson_state(user, lesson)),
            "assegnata": lesson.id in assigned,
        })
    return Response({area: by_area.get(area, []) for area in ["GRA", "VOC", "COM"]})


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def lesson_detail(request, lesson_id):
    """Il contenuto teorico è sempre pubblico. Stato personale, assegnazione e risultato
    dell'ultimo esercizio sono inclusi soltanto per chi ha effettuato l'accesso."""
    lesson = get_object_or_404(
        Lezione.objects.select_related("area", "tipologia", "livello", "difficolta").prefetch_related("sezioni", "quiz__quesiti_guidati", "quiz__quesiti_finali"),
        id=lesson_id, stato_id__in=STATI_LEZIONE_ESPOSTI,
    )
    user = request.user if request.user.is_authenticated else None
    if lesson.stato_id != "PUBBLICATA":
        return Response({
            "id": lesson.id, "area": lesson.area_id, "tipologia": lesson.tipologia.nome,
            "nome": lesson.nome, "descrizione": lesson.descrizione, "categoria": lesson.categoria,
            "livello": lesson.livello_id, "difficolta": lesson.difficolta_id,
            "ordine_percorso": lesson.ordine_percorso, "ordine_mvp": lesson.ordine_mvp,
            "obiettivo_didattico": lesson.obiettivo_didattico,
            "competenze": lesson.competenze, "durata_min": lesson.durata_min,
            "errori_tipici": lesson.errori_tipici,
            "fase_roadmap": lesson.fase_roadmap,
            "sezioni": [], "quiz": [],
            "in_preparazione": True, "stato_utente": STATO_IN_PREPARAZIONE,
            "assegnata": False, "autenticato": bool(user),
        })
    progress = Progresso.objects.filter(utente=user, lezione=lesson).first() if user else None
    missing = [{"id": item.id, "nome": item.nome} for item in missing_prerequisites(user, lesson)] if user else []
    return Response({
        **LessonDetailSerializer(lesson).data, "in_preparazione": False,
        "stato_utente": lesson_state(user, lesson) if user else None,
        "prerequisiti_consigliati": missing,
        "assegnata": bool(progress and progress.assegnata),
        "ultimo_risultato": progress.punteggio if progress and progress.punteggio else None,
        "autenticato": bool(user),
    })


@api_view(["POST", "DELETE"])
def lesson_assignment(request, lesson_id):
    """Aggiunge o rimuove la lezione dal percorso personale. Solo utenti autenticati (IsAuthenticated di default)."""
    lesson = get_object_or_404(Lezione, id=lesson_id, stato_id="PUBBLICATA")
    if request.method == "DELETE":
        progress = unassign_lesson(request.user, lesson)
    else:
        progress = assign_lesson(request.user, lesson)
    return Response(ProgressSerializer(progress).data if progress else {"assegnata": False})


@api_view(["POST"])
def start_lesson(request, lesson_id):
    lesson = get_object_or_404(Lezione, id=lesson_id, stato_id="PUBBLICATA")
    progress = mark_in_progress(request.user, lesson)
    return Response(ProgressSerializer(progress).data)


# Dopo la separazione in due tabelle, l'id del quesito e' univoco solo
# all'interno della propria modalita': la rotta deve quindi dichiararla.
QUESTION_MODELS = {
    StrutturaQuiz.GUIDATO: QuesitoGuidato,
    StrutturaQuiz.FINALE: QuesitoFinale,
}


@api_view(["POST"])
def check_answer(request, lesson_id, modalita, question_id):
    model = QUESTION_MODELS.get(modalita)
    if model is None:
        return Response({"detail": f"Modalita' quiz sconosciuta: {modalita}"}, status=status.HTTP_404_NOT_FOUND)
    question = get_object_or_404(
        model.objects.select_related("quiz__lezione"),
        id=question_id, quiz__lezione_id=lesson_id,
        quiz__lezione__stato_id="PUBBLICATA",
    )
    correct = _answer_matches(question, request.data.get("risposta"))
    return Response({"corretta": correct, "risposta_corretta": _display_answer(question), "spiegazione": question.spiegazione})


@api_view(["POST"])
def submit_final_quiz(request, lesson_id):
    lesson = get_object_or_404(Lezione, id=lesson_id, stato_id="PUBBLICATA")
    quiz = get_object_or_404(StrutturaQuiz.objects.prefetch_related("quesiti_finali"), lezione=lesson, modalita=StrutturaQuiz.FINALE)
    answers = request.data.get("risposte", {})
    questions = list(quiz.quesiti_finali.all())
    correct = sum(_answer_matches(question, answers.get(str(question.id), answers.get(question.id))) for question in questions)
    score = round(correct / len(questions) * 100) if questions else 0
    try:
        progress = record_final_score(request.user, lesson, score, int(request.data.get("minuti", 0)))
    except (ValueError, TypeError) as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    details = [{
        "quesito_id": question.id, "corretta": _answer_matches(question, answers.get(str(question.id), answers.get(question.id))),
        "risposta_corretta": _display_answer(question), "spiegazione": question.spiegazione,
    } for question in questions]
    return Response({
        "punteggio": score, "miglior_punteggio": progress.punteggio,
        "superato": score >= 70, "stato": progress.stato, "risultati": details,
    })


@api_view(["GET"])
def progress_list(request):
    """Le lezioni che l'utente ha assegnato al proprio percorso personale."""
    progress = Progresso.objects.filter(utente=request.user, assegnata=True).select_related("lezione").order_by("-completata_il", "lezione__nome")
    return Response(ProgressSerializer(progress, many=True).data)


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def content_gaps(request):
    lessons = Lezione.objects.filter(ordine_mvp__isnull=False).select_related(
        "area", "stato"
    ).prefetch_related("sezioni", "quiz").order_by("ordine_mvp", "ordine_percorso")
    rows = []
    total_todo = 0
    missing_final_quiz = 0
    for lesson in lessons:
        todo_sections = [
            {"ordine": section.ordine, "tipo_sezione": section.tipo_sezione}
            for section in lesson.sezioni.all()
            if str(section.contenuto.get("todo", "")).startswith("TODO_FONTE:")
        ]
        has_final = any(quiz.modalita == StrutturaQuiz.FINALE for quiz in lesson.quiz.all())
        total_todo += len(todo_sections)
        missing_final_quiz += not has_final
        rows.append({
            "id": lesson.id, "nome": lesson.nome, "area": lesson.area_id,
            "ordine_mvp": lesson.ordine_mvp,
            "stato_sorgente": lesson.stato.nome,
            "sezioni_todo": todo_sections, "quiz_finale_mancante": not has_final,
        })
    return Response({
        "riepilogo": {"lezioni_mvp": len(rows), "sezioni_todo": total_todo, "quiz_finali_mancanti": missing_final_quiz},
        "lezioni": rows,
    })
