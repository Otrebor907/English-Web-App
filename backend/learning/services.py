from collections import defaultdict, deque
from django.db import transaction
from django.utils import timezone
from .models import Lezione, Progresso


PASS_THRESHOLD = 70


class GraphValidationError(ValueError):
    def __init__(self, errors):
        self.errors = errors if isinstance(errors, list) else [str(errors)]
        super().__init__("DAG non valido:\n- " + "\n- ".join(self.errors))


def collect_lesson_graph_errors(lessons, prerequisites):
    """Return every detectable graph error instead of stopping at the first one."""
    errors = []
    by_id = {row["id"]: row for row in lessons}
    if len(by_id) != len(lessons):
        errors.append("ID lezione duplicato nel file sorgente")

    incoming = defaultdict(set)
    outgoing = defaultdict(set)
    bad_order = []
    for edge in prerequisites:
        lesson_id = edge["lezione_id"]
        required_id = edge["richiede_lezione_id"]
        if lesson_id not in by_id:
            errors.append(f"Prerequisito fuori perimetro: lezione inesistente {lesson_id}")
            continue
        if required_id not in by_id:
            errors.append(f"Prerequisito fuori perimetro o inesistente: {lesson_id} richiede {required_id}")
            continue
        if by_id[lesson_id].get("ordine_mvp") is not None and by_id[required_id].get("ordine_mvp") is None:
            errors.append(
                f"Prerequisito fuori perimetro MVP: {lesson_id} richiede {required_id}, non presente nel Percorso MVP"
            )
        if by_id[required_id]["ordine_percorso"] >= by_id[lesson_id]["ordine_percorso"]:
            bad_order.append((required_id, lesson_id))
        incoming[lesson_id].add(required_id)
        outgoing[required_id].add(lesson_id)

    indegree = {lesson_id: len(incoming[lesson_id]) for lesson_id in by_id}
    queue = deque(sorted(lesson_id for lesson_id, degree in indegree.items() if degree == 0))
    visited = []
    while queue:
        current = queue.popleft()
        visited.append(current)
        for child in outgoing[current]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if len(visited) != len(by_id):
        cyclic = sorted(set(by_id) - set(visited))
        errors.append(f"Ciclo nel grafo dei prerequisiti: {', '.join(cyclic)}")
    for required_id, lesson_id in bad_order:
        errors.append(f"Ordine prerequisito non valido: {required_id} deve precedere {lesson_id}")

    published = [row for row in lessons if row.get("stato") == "PUBBLICATA" and row.get("ordine_mvp") is not None]
    if published:
        published_ids = {row["id"] for row in published}
        initial = min(published, key=lambda row: row["ordine_mvp"])["id"]
        if incoming[initial]:
            errors.append(
                f"Il nodo iniziale {initial} non può avere prerequisiti: {', '.join(sorted(incoming[initial]))}"
            )
        reachable = {initial}
        queue = deque([initial])
        while queue:
            for child in outgoing[queue.popleft()]:
                if child in published_ids and child not in reachable:
                    reachable.add(child)
                    queue.append(child)
        unreachable = sorted(row["id"] for row in published if row["id"] not in reachable)
        if unreachable:
            errors.append(
                f"Lezioni pubblicate non raggiungibili dal nodo iniziale {initial}: {', '.join(unreachable)}"
            )
    return errors


def validate_lesson_graph(lessons, prerequisites):
    """Validate references, ordering, cycles and reachability of the published MVP."""
    errors = collect_lesson_graph_errors(lessons, prerequisites)
    if errors:
        raise GraphValidationError(errors)


def completed_lesson_ids(user):
    return set(Progresso.objects.filter(utente=user, stato=Progresso.COMPLETATA).values_list("lezione_id", flat=True))


def lesson_state(user, lesson, completed=None):
    completed = completed if completed is not None else completed_lesson_ids(user)
    progress = Progresso.objects.filter(utente=user, lezione=lesson).first()
    if progress and progress.stato == Progresso.COMPLETATA:
        return Progresso.COMPLETATA
    required = set(lesson.vincoli.values_list("richiede_lezione_id", flat=True))
    if not required.issubset(completed):
        return Progresso.BLOCCATA
    return progress.stato if progress and progress.stato == Progresso.IN_CORSO else Progresso.DISPONIBILE


def missing_prerequisites(user, lesson, completed=None):
    completed = completed if completed is not None else completed_lesson_ids(user)
    return lesson.prerequisiti.exclude(id__in=completed).order_by("ordine_mvp", "ordine_percorso")


@transaction.atomic
def sync_progress(user):
    """Persist every state while recomputing locked/available from the DAG."""
    completed = completed_lesson_ids(user)
    for lesson in Lezione.objects.filter(ordine_mvp__isnull=False, stato_id="PUBBLICATA").prefetch_related("vincoli"):
        progress, _ = Progresso.objects.get_or_create(utente=user, lezione=lesson)
        if progress.stato in {Progresso.COMPLETATA, Progresso.IN_CORSO}:
            continue
        required = set(lesson.vincoli.values_list("richiede_lezione_id", flat=True))
        expected = Progresso.DISPONIBILE if required.issubset(completed) else Progresso.BLOCCATA
        if progress.stato != expected:
            progress.stato = expected
            progress.save(update_fields=["stato"])


def mark_in_progress(user, lesson):
    if lesson_state(user, lesson) == Progresso.BLOCCATA:
        raise ValueError("La lezione è bloccata dai prerequisiti")
    progress, _ = Progresso.objects.get_or_create(utente=user, lezione=lesson)
    if progress.stato != Progresso.COMPLETATA:
        progress.stato = Progresso.IN_CORSO
        progress.save(update_fields=["stato"])
    return progress


@transaction.atomic
def record_final_score(user, lesson, score, minutes=0):
    if lesson_state(user, lesson) == Progresso.BLOCCATA:
        raise ValueError("La lezione è bloccata dai prerequisiti")
    progress, _ = Progresso.objects.get_or_create(utente=user, lezione=lesson)
    progress.punteggio = max(progress.punteggio, score)
    progress.minuti_effettivi += max(0, minutes)
    if score >= PASS_THRESHOLD:
        progress.stato = Progresso.COMPLETATA
        progress.completata_il = progress.completata_il or timezone.now()
    elif progress.stato != Progresso.COMPLETATA:
        progress.stato = Progresso.IN_CORSO
    progress.save()
    sync_progress(user)
    return progress
