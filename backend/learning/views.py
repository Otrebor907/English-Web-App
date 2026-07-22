from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import Lezione, Progresso, Quesito, Quiz
from .serializers import LessonDetailSerializer, LoginSerializer, ProgressSerializer, RegisterSerializer, UserSerializer
from .services import completed_lesson_ids, lesson_state, mark_in_progress, missing_prerequisites, record_final_score, sync_progress


def _answer_matches(question, answer):
    if answer is None:
        return False
    if question.tipo == Quesito.COMPLETAMENTO:
        return str(answer).strip().casefold() == question.risposta_corretta.strip().casefold()
    return str(answer) == question.risposta_corretta


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "utente": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data["user"]
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "utente": UserSerializer(user).data})


@api_view(["GET"])
def profile(request):
    return Response(UserSerializer(request.user).data)


@api_view(["GET"])
def path_lessons(request):
    sync_progress(request.user)
    lessons = Lezione.objects.filter(ordine_mvp__isnull=False, stato_id="PUBBLICATA").select_related(
        "area", "livello", "difficolta", "importanza_mvp"
    ).prefetch_related("prerequisiti").order_by("ordine_mvp")
    completed = completed_lesson_ids(request.user)
    payload = []
    for lesson in lessons:
        missing = missing_prerequisites(request.user, lesson, completed)
        progress = Progresso.objects.filter(utente=request.user, lezione=lesson).first()
        payload.append({
            "id": lesson.id, "nome": lesson.nome, "descrizione": lesson.descrizione,
            "area": lesson.area_id, "livello": lesson.livello_id, "durata_min": lesson.durata_min,
            "priorita": lesson.priorita, "ordine_mvp": lesson.ordine_mvp,
            "importanza_mvp": lesson.importanza_mvp_id,
            "stato": lesson_state(request.user, lesson, completed),
            "punteggio": progress.punteggio if progress else 0,
            "prerequisiti_mancanti": [{"id": item.id, "nome": item.nome} for item in missing],
        })
    return Response(payload)


@api_view(["GET"])
def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(
        Lezione.objects.select_related("area", "tipologia", "livello", "difficolta", "importanza_mvp").prefetch_related("sezioni", "quiz__quesiti"),
        id=lesson_id, ordine_mvp__isnull=False, stato_id="PUBBLICATA",
    )
    state = lesson_state(request.user, lesson)
    if state == Progresso.BLOCCATA:
        missing = [{"id": item.id, "nome": item.nome} for item in missing_prerequisites(request.user, lesson)]
        return Response({"detail": "Lezione bloccata", "prerequisiti_mancanti": missing}, status=status.HTTP_403_FORBIDDEN)
    return Response({**LessonDetailSerializer(lesson).data, "stato_utente": state})


@api_view(["POST"])
def start_lesson(request, lesson_id):
    lesson = get_object_or_404(Lezione, id=lesson_id, ordine_mvp__isnull=False, stato_id="PUBBLICATA")
    try:
        progress = mark_in_progress(request.user, lesson)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    return Response(ProgressSerializer(progress).data)


@api_view(["POST"])
def check_answer(request, lesson_id, question_id):
    question = get_object_or_404(Quesito.objects.select_related("quiz__lezione"), id=question_id, quiz__lezione_id=lesson_id)
    if lesson_state(request.user, question.quiz.lezione) == Progresso.BLOCCATA:
        return Response({"detail": "Lezione bloccata"}, status=status.HTTP_403_FORBIDDEN)
    correct = _answer_matches(question, request.data.get("risposta"))
    return Response({"corretta": correct, "risposta_corretta": question.risposta_corretta, "spiegazione": question.spiegazione})


@api_view(["POST"])
def submit_final_quiz(request, lesson_id):
    lesson = get_object_or_404(Lezione, id=lesson_id, ordine_mvp__isnull=False, stato_id="PUBBLICATA")
    quiz = get_object_or_404(Quiz.objects.prefetch_related("quesiti"), lezione=lesson, modalita=Quiz.FINALE)
    answers = request.data.get("risposte", {})
    questions = list(quiz.quesiti.all())
    correct = sum(_answer_matches(question, answers.get(str(question.id), answers.get(question.id))) for question in questions)
    score = round(correct / len(questions) * 100) if questions else 0
    try:
        progress = record_final_score(request.user, lesson, score, int(request.data.get("minuti", 0)))
    except (ValueError, TypeError) as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    details = [{
        "quesito_id": question.id, "corretta": _answer_matches(question, answers.get(str(question.id), answers.get(question.id))),
        "risposta_corretta": question.risposta_corretta, "spiegazione": question.spiegazione,
    } for question in questions]
    return Response({
        "punteggio": score, "miglior_punteggio": progress.punteggio,
        "superato": score >= 70, "stato": progress.stato, "risultati": details,
    })


@api_view(["GET"])
def progress_list(request):
    sync_progress(request.user)
    progress = Progresso.objects.filter(utente=request.user).select_related("lezione").order_by("lezione__ordine_mvp")
    return Response(ProgressSerializer(progress, many=True).data)


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
def content_gaps(request):
    lessons = Lezione.objects.filter(ordine_mvp__isnull=False).select_related(
        "area", "stato"
    ).prefetch_related("sezioni", "quiz").order_by("priorita", "ordine_mvp")
    rows = []
    total_todo = 0
    missing_final_quiz = 0
    for lesson in lessons:
        todo_sections = [
            {"ordine": section.ordine, "tipo_sezione": section.tipo_sezione}
            for section in lesson.sezioni.all()
            if str(section.contenuto.get("todo", "")).startswith("TODO_FONTE:")
        ]
        has_final = any(quiz.modalita == Quiz.FINALE for quiz in lesson.quiz.all())
        total_todo += len(todo_sections)
        missing_final_quiz += not has_final
        rows.append({
            "id": lesson.id, "nome": lesson.nome, "area": lesson.area_id,
            "priorita": lesson.priorita, "ordine_mvp": lesson.ordine_mvp,
            "stato_sorgente": lesson.stato.nome,
            "sezioni_todo": todo_sections, "quiz_finale_mancante": not has_final,
        })
    return Response({
        "riepilogo": {"lezioni_mvp": len(rows), "sezioni_todo": total_todo, "quiz_finali_mancanti": missing_final_quiz},
        "lezioni": rows,
    })
