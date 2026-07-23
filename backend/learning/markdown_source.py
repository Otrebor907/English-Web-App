"""Parser dei brief editoriali markdown (lezioni_markdown/**/*.md) verso il modello dati.

Il brief è la fonte editoriale definitiva della lezione. Questo modulo NON inventa
contenuti: estrae soltanto ciò che è scritto nel file (teoria, esercizio guidato,
quiz finale con soluzioni) e lo trasforma in sezioni + quiz importabili.

La pubblicazione è mirata a una singola lezione: aggiorna la Lezione esistente
(sezioni + quiz) e la porta in stato PUBBLICATA senza toccare le altre lezioni.
"""
import re
from pathlib import Path

from django.db import transaction

from .models import Lezione, Quesito, Quiz, SezioneLezione, StatoLezione


CONTENT_HEADING = "Contenuto definitivo da pubblicare"
GUIDED_HEADING = "Esercizio guidato"
FINAL_HEADING = "Esercizio finale"
SOLUTIONS_HEADING = "Soluzioni e spiegazioni"
# Heading di teoria che NON diventano sezioni di contenuto.
NON_SECTION = {GUIDED_HEADING, FINAL_HEADING, SOLUTIONS_HEADING}


def _strip_md(text):
    """Rimuove enfasi markdown (**, *, `) mantenendo il testo."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text.strip()


def _parse_frontmatter(text):
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise ValueError("Frontmatter YAML mancante nel brief markdown")
    meta = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip('"')
    return meta, text[match.end():]


def _split_h3_blocks(body):
    """Ritorna [(heading, corpo)] per ogni '### ' nel blocco fornito."""
    parts = re.split(r"^### +", body, flags=re.MULTILINE)
    blocks = []
    for part in parts[1:]:
        head, _, rest = part.partition("\n")
        blocks.append((head.strip(), rest.strip()))
    return blocks


def _bullet_lines(body):
    return [line[2:].strip() for line in body.splitlines() if line.strip().startswith("- ")]


def _table_rows(body):
    rows = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= {"-", " "} for c in cells):  # riga separatrice
            continue
        rows.append(cells)
    return rows


def _section_from_block(heading, body):
    """Trasforma un blocco di teoria in una sezione (contenuto + formato_web)."""
    bullets = _bullet_lines(body)
    # Errori tipici: righe "❌ ... → ✅ ... — perché" → box multipli ❌/✅/perché.
    if "❌" in body and "✅" in body:
        errori = []
        for line in bullets:
            m = re.match(r"❌\s*(.+?)\s*→\s*✅\s*(.+?)\s*—\s*(.+)", line)
            if m:
                errori.append({
                    "errato": _strip_md(m.group(1)),
                    "corretto": _strip_md(m.group(2)),
                    "perche": _strip_md(m.group(3)),
                })
        if errori:
            return {"tipo_sezione": heading, "formato_web": "errore_box",
                    "contenuto": {"titolo": heading, "errori": errori}}
    # Tabella → lista di righe leggibili.
    rows = _table_rows(body)
    if rows:
        elementi = [" — ".join(_strip_md(c) for c in row) for row in rows[1:]]  # salta l'header
        return {"tipo_sezione": heading, "formato_web": "lista",
                "contenuto": {"titolo": heading, "elementi": elementi}}
    # Elenco puntato → lista.
    if bullets:
        return {"tipo_sezione": heading, "formato_web": "lista",
                "contenuto": {"titolo": heading, "elementi": [_strip_md(b) for b in bullets]}}
    # Altrimenti testo semplice (paragrafi uniti).
    testo = " ".join(_strip_md(p) for p in body.split("\n") if p.strip())
    return {"tipo_sezione": heading, "formato_web": "testo",
            "contenuto": {"titolo": heading, "testo": testo}}


def _numbered_items(body):
    """Ritorna [(numero, testo)] dagli elenchi numerati '1. ...' (multi-riga safe)."""
    items = {}
    current = None
    for line in body.splitlines():
        m = re.match(r"\s*(\d+)\.\s+(.*)", line)
        if m:
            current = int(m.group(1))
            items[current] = m.group(2).strip()
        elif current is not None and line.strip():
            items[current] += " " + line.strip()
    return [(k, items[k]) for k in sorted(items)]


def _parse_guided(body):
    """Esercizio guidato: item con « **Risposta: X.** » → quesiti di completamento."""
    quesiti = []
    for ordine, (num, text) in enumerate(_numbered_items(body), start=1):
        m = re.search(r"\*\*Risposta:\s*(.+?)\.?\*\*", text)
        if not m:
            continue
        risposta = _strip_md(m.group(1)).rstrip(".")
        testo = _strip_md(re.sub(r"\*\*Risposta:.*?\*\*", "", text)).strip()
        quesiti.append({
            "ordine": ordine, "tipo": Quesito.COMPLETAMENTO, "testo": testo,
            "opzioni": [], "risposta_corretta": risposta,
            "spiegazione": f"Risposta corretta: «{risposta}».",
        })
    return quesiti


def _parse_solution(text):
    """Da « **risposta**. spiegazione » estrae (risposta, spiegazione).
    Le varianti « A / B » diventano « A|B » per il match multi-risposta."""
    m = re.match(r"\*\*(.+?)\*\*\.?\s*(.*)", text)
    if not m:
        return _strip_md(text), ""
    risposta = m.group(1).strip()
    risposta = "|".join(part.strip() for part in risposta.split(" / "))
    return risposta, _strip_md(m.group(2)).strip()


def _parse_final(questions_body, solutions_body):
    """Quiz finale: appaia le domande numerate con le soluzioni numerate.
    « Scegli: A / B » → scelta multipla; il resto → completamento."""
    questions = dict(_numbered_items(questions_body))
    solutions = dict(_numbered_items(solutions_body))
    quesiti = []
    for ordine, num in enumerate(sorted(questions), start=1):
        raw = questions[num]
        risposta, spiegazione = _parse_solution(solutions.get(num, ""))
        opzioni = []
        tipo = Quesito.COMPLETAMENTO
        testo = _strip_md(raw)
        if raw.strip().lower().startswith("scegli:"):
            tipo = Quesito.SCELTA_MULTIPLA
            choice_part = raw.split(":", 1)[1]
            opzioni = [_strip_md(o) for o in choice_part.split("/") if o.strip()]
            testo = "Scegli la frase corretta."
            # la risposta della soluzione deve combaciare con un'opzione
            if risposta not in opzioni:
                match = next((o for o in opzioni if o.casefold() == risposta.casefold()), None)
                risposta = match or risposta
        quesiti.append({
            "ordine": ordine, "tipo": tipo, "testo": testo,
            "opzioni": opzioni, "risposta_corretta": risposta,
            "spiegazione": spiegazione,
        })
    return quesiti


def parse_markdown_lesson(path):
    """Parsa un brief markdown in {id, sezioni, guidato, finale}."""
    text = Path(path).read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    lesson_id = meta.get("id")
    if not lesson_id:
        raise ValueError("Campo 'id' mancante nel frontmatter")

    # Isola il blocco "## Contenuto definitivo da pubblicare" fino al prossimo "## ".
    m = re.search(r"^## +" + re.escape(CONTENT_HEADING) + r"\s*\n(.*?)(?=^## )", body, re.DOTALL | re.MULTILINE)
    if not m:
        raise ValueError("Blocco 'Contenuto definitivo da pubblicare' non trovato")
    content_block = m.group(1)

    sezioni, guidato, finale = [], [], []
    final_body = solutions_body = ""
    for heading, block in _split_h3_blocks(content_block):
        if heading == GUIDED_HEADING:
            guidato = _parse_guided(block)
        elif heading == FINAL_HEADING:
            final_body = block
        elif heading == SOLUTIONS_HEADING:
            solutions_body = block
        elif heading not in NON_SECTION:
            sezioni.append(_section_from_block(heading, block))
    if final_body and solutions_body:
        finale = _parse_final(final_body, solutions_body)

    return {"id": lesson_id, "sezioni": sezioni, "guidato": guidato, "finale": finale}


@transaction.atomic
def publish_markdown_lesson(path):
    """Pubblica una singola lezione dal brief: sostituisce sezioni e quiz della sola
    lezione indicata e la porta in stato PUBBLICATA. Non tocca le altre lezioni."""
    data = parse_markdown_lesson(path)
    lesson = Lezione.objects.get(id=data["id"])

    # Sezioni: rimpiazza solo quelle di questa lezione.
    SezioneLezione.objects.filter(lezione=lesson).delete()
    SezioneLezione.objects.bulk_create([
        SezioneLezione(
            lezione=lesson, ordine=i, tipo_sezione=s["tipo_sezione"],
            contenuto=s["contenuto"], formato_web=s["formato_web"],
        )
        for i, s in enumerate(data["sezioni"], start=1)
    ])

    # Quiz: rimpiazza solo quelli di questa lezione.
    Quiz.objects.filter(lezione=lesson).delete()
    for modalita, titolo, quesiti in (
        (Quiz.GUIDATO, "Esercizio guidato", data["guidato"]),
        (Quiz.FINALE, "Quiz finale", data["finale"]),
    ):
        if not quesiti:
            continue
        quiz = Quiz.objects.create(lezione=lesson, modalita=modalita, titolo=titolo)
        Quesito.objects.bulk_create([Quesito(quiz=quiz, **q) for q in quesiti])

    # Pubblica (garantendo l'esistenza della lookup di stato).
    StatoLezione.objects.get_or_create(code="PUBBLICATA", defaults={"nome": "Pubblicata"})
    lesson.stato_id = "PUBBLICATA"
    lesson.save(update_fields=["stato"])

    return {
        "id": lesson.id, "sezioni": len(data["sezioni"]),
        "guidato": len(data["guidato"]), "finale": len(data["finale"]),
    }
