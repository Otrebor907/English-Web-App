from django.db import transaction
from django.utils import timezone
from .models import Lezione, Progresso, User


PASS_THRESHOLD = 70


def authenticate_by_email(email, password):
    """Verifica le credenziali e restituisce l'utente, oppure None.

    Sostituisce django.contrib.auth.authenticate(): quell'app non e' piu'
    installata (e' sparita con il pannello /admin/). Replica la stessa logica
    di ModelBackend, compresa la difesa contro il timing attack: se l'email non
    esiste si calcola comunque un hash, altrimenti una risposta molto piu'
    rapida rivelerebbe a un attaccante quali email sono registrate.
    """
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        User().set_password(password)
        return None
    if user.check_password(password) and user.is_active:
        return user
    return None


def completed_lesson_ids(user):
    return set(Progresso.objects.filter(utente=user, stato=Progresso.COMPLETATA).values_list("lezione_id", flat=True))


def lesson_state(user, lesson):
    """Stato di avanzamento dell'utente sulla lezione.
    Nessuna lezione e' mai bloccata: l'ordine e' un suggerimento (ordine_mvp), non un cancello."""
    progress = Progresso.objects.filter(utente=user, lezione=lesson).first()
    if progress and progress.stato == Progresso.COMPLETATA:
        return Progresso.COMPLETATA
    return progress.stato if progress and progress.stato == Progresso.IN_CORSO else Progresso.DISPONIBILE


@transaction.atomic
def sync_progress(user):
    """Garantisce un record di progresso per ogni lezione MVP pubblicata."""
    for lesson in Lezione.objects.filter(ordine_mvp__isnull=False, stato_id="PUBBLICATA"):
        Progresso.objects.get_or_create(utente=user, lezione=lesson)


def mark_in_progress(user, lesson):
    progress, _ = Progresso.objects.get_or_create(utente=user, lezione=lesson)
    if progress.stato != Progresso.COMPLETATA:
        progress.stato = Progresso.IN_CORSO
        progress.save(update_fields=["stato"])
    return progress


def assigned_lesson_ids(user):
    """Lezioni che l'utente ha aggiunto al proprio percorso personale."""
    return set(Progresso.objects.filter(utente=user, assegnata=True).values_list("lezione_id", flat=True))


def assign_lesson(user, lesson):
    """Aggiunge la lezione al percorso personale — organizzativo, non un cancello d'accesso."""
    progress, _ = Progresso.objects.get_or_create(utente=user, lezione=lesson)
    if not progress.assegnata:
        progress.assegnata = True
        progress.save(update_fields=["assegnata"])
    return progress


def unassign_lesson(user, lesson):
    """Rimuove la lezione dal percorso personale. Punteggio e cronologia restano intatti."""
    progress = Progresso.objects.filter(utente=user, lezione=lesson).first()
    if progress and progress.assegnata:
        progress.assegnata = False
        progress.save(update_fields=["assegnata"])
    return progress


@transaction.atomic
def record_final_score(user, lesson, score):
    progress, _ = Progresso.objects.get_or_create(utente=user, lezione=lesson)
    progress.punteggio = max(progress.punteggio, score)
    if score >= PASS_THRESHOLD:
        progress.stato = Progresso.COMPLETATA
        progress.completata_il = progress.completata_il or timezone.now()
        progress.assegnata = True  # completare un esercizio propone automaticamente la lezione nel percorso
    elif progress.stato != Progresso.COMPLETATA:
        progress.stato = Progresso.IN_CORSO
    progress.save()
    sync_progress(user)
    return progress
