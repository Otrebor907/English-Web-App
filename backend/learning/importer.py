import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from django.db import transaction
from openpyxl import load_workbook
from .models import (
    Area, Difficolta, Lezione, Livello, QuesitoFinale, QuesitoGuidato,
    StatoLezione, StrutturaLezione, StrutturaQuiz, Tipologia,
)


LOOKUP_MODELS = {
    "area": Area,
    "tipologia": Tipologia,
    "livello": Livello,
    "difficolta": Difficolta,
    "stato": StatoLezione,
}
SUPPORTED_AREAS = {"GRA", "VOC", "COM"}
AREA_SECTION_COUNTS = {"GRA": 9, "VOC": 7, "COM": 8}
CATALOG_LESSON_COUNT = 98
MVP_LESSON_COUNT = 29
REQUIRED_LESSON_FIELDS = {
    "id", "area", "tipologia", "nome", "livello", "difficolta", "ordine_percorso",
    "obiettivo_didattico", "competenze", "durata_min", "errori_tipici", "stato",
}
REQUIRED_COMPLETE_SOURCE_KEYS = {"liste", "lezioni", "sezioni", "quiz"}


def _json_cell(value, default):
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value)


def _sheet_rows(sheet):
    rows = list(sheet.values)
    if not rows:
        return []
    headers = [str(value).strip() if value is not None else "" for value in rows[0]]
    return [{headers[i]: value for i, value in enumerate(row) if headers[i]} for row in rows[1:] if any(value is not None for value in row)]


def _sheet_rows_at(sheet, header_row, max_column=None, max_row=None):
    rows = sheet.iter_rows(min_row=header_row, max_row=max_row, values_only=True, max_col=max_column)
    headers = [str(value).strip() if value is not None else "" for value in next(rows)]
    return [
        {headers[index]: value for index, value in enumerate(row) if headers[index]}
        for row in rows if any(value is not None for value in row)
    ]


def _code(value):
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]+", "_", normalized.upper()).strip("_")


def _split_list(value):
    if value in (None, "", "—") or str(value).strip().casefold() in {"nessuno", "nessuna"}:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _with_expected_counts(data, fixture=False):
    meta = data.setdefault("meta", {})
    meta.setdefault("catalogo_atteso", len(data.get("lezioni", [])) if fixture else CATALOG_LESSON_COUNT)
    meta.setdefault(
        "mvp_atteso",
        sum(row.get("ordine_mvp") is not None for row in data.get("lezioni", [])) if fixture else MVP_LESSON_COUNT,
    )
    return data


def _audio_field_paths(value, path="fonte"):
    paths = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if "audio" in str(key).casefold():
                paths.append(child_path)
            paths.extend(_audio_field_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(_audio_field_paths(child, f"{path}[{index}]"))
    return paths


def _reject_incomplete_json_fragment(data):
    if not isinstance(data, dict) or "id" not in data or "lezioni" in data:
        return
    missing_lesson_fields = sorted(
        field for field in REQUIRED_LESSON_FIELDS if data.get(field) in (None, "")
    )
    missing_blocks = sorted(REQUIRED_COMPLETE_SOURCE_KEYS)
    details = []
    if missing_lesson_fields:
        details.append(f"campi lezione mancanti: {', '.join(missing_lesson_fields)}")
    details.append(f"blocchi catalogo mancanti: {', '.join(missing_blocks)}")
    raise ValueError(
        f"Frammento JSON della lezione {data['id']} riconosciuto ma non importabile come catalogo completo; "
        + "; ".join(details)
    )


def _load_programma_workbook(workbook):
    """Map the supplied planning workbook without treating planned copy as finished content."""
    area_codes = {}
    for row in workbook["Liste"].iter_rows(min_row=16, max_row=18, min_col=1, max_col=2, values_only=True):
        if row[0] and row[1]:
            area_codes[str(row[0])] = str(row[1])

    list_columns = {
        "Area Didattica": "area", "Tipologia Lezione": "tipologia",
        "Livello Linguistico": "livello", "Difficoltà": "difficolta",
        "Stato della Lezione": "stato",
    }
    lists = defaultdict(list)
    seen = defaultdict(set)
    for row in _sheet_rows_at(workbook["Liste"], 4, 8, max_row=10):
        for source_name, target_name in list_columns.items():
            value = row.get(source_name)
            if not value:
                continue
            code = area_codes.get(str(value), str(value)) if target_name == "area" else (
                str(value) if target_name in {"livello", "difficolta"} else _code(value)
            )
            if code not in seen[target_name]:
                lists[target_name].append({"code": code, "nome": str(value)})
                seen[target_name].add(code)

    mvp = {}
    for row in _sheet_rows_at(workbook["Percorso MVP"], 4, 9):
        lesson_id = row.get("ID Lezione")
        if not lesson_id or not isinstance(row.get("Ordine MVP"), (int, float)):
            continue
        mvp[str(lesson_id)] = {"ordine_mvp": int(row["Ordine MVP"])}

    normalized_mvp = False
    if "GRA-A1-008" not in mvp and "GRA-A1-009" in mvp:
        insertion_order = mvp["GRA-A1-009"]["ordine_mvp"]
        for item in mvp.values():
            if item["ordine_mvp"] >= insertion_order:
                item["ordine_mvp"] += 1
        mvp["GRA-A1-008"] = {"ordine_mvp": insertion_order}
        normalized_mvp = True

    lessons = []
    for row in _sheet_rows_at(workbook["Programma Lezioni"], 4, 17):
        lesson_id = row.get("ID Lezione")
        if not lesson_id:
            continue
        lesson_id = str(lesson_id)
        mvp_row = mvp.get(lesson_id)
        lessons.append({
            "id": lesson_id,
            "area": area_codes[str(row["Area Didattica"])],
            "tipologia": _code(row["Tipologia Lezione"]),
            "nome": str(row["Nome Lezione"]),
            "descrizione": str(row.get("Breve Descrizione") or ""),
            "categoria": str(row.get("Categoria") or "").strip(),
            "livello": str(row["Livello Linguistico"]),
            "difficolta": str(row["Difficoltà"]),
            "ordine_percorso": int(row["Ordine nel Percorso"]),
            "obiettivo_didattico": str(row["Obiettivo Didattico"]),
            "competenze": _split_list(row.get("Competenze Allenate")),
            "durata_min": int(row["Durata Stimata (min)"]),
            "errori_tipici": [str(row["Errori Tipici degli Italiani"])],
            "stato": _code(row["Stato della Lezione"]),
            "ordine_mvp": mvp_row["ordine_mvp"] if mvp_row else None,
        })

    template_sheets = {"GRA": "Grammatica", "VOC": "Vocabolario", "COM": "Comunicazione"}
    templates = {}
    for area, sheet_name in template_sheets.items():
        templates[area] = []
        for row in _sheet_rows_at(workbook[sheet_name], 4, 5):
            if not isinstance(row.get("Ordine"), (int, float)):
                break
            templates[area].append({
                "ordine": int(row["Ordine"]),
                "tipo_sezione": str(row["Sezione della Lezione"]),
                "contenuto": {
                    "titolo": str(row["Sezione della Lezione"]),
                    "todo": f"TODO_FONTE: {row['Contenuto Previsto']}",
                    "obiettivo_template": str(row["Obiettivo"]),
                    "formato_sorgente": str(row["Formato Web App"]),
                },
                "formato_web": "todo",
            })
    sections = [
        {"lezione_id": lesson["id"], **section}
        for lesson in lessons for section in templates[lesson["area"]]
    ]
    return {
        "liste": dict(lists), "lezioni": lessons,
        "sezioni": sections, "quiz": [],
        "meta": {
            "formato": "programma_lezioni",
            "catalogo_atteso": CATALOG_LESSON_COUNT,
            "mvp_atteso": MVP_LESSON_COUNT,
            "mvp_normalizzato": normalized_mvp,
            "quiz_mancanti": True,
            "contenuti_sezioni_todo": True,
        },
    }


def load_source(path):
    path = Path(path)
    if path.suffix.lower() == ".json":
        with path.open(encoding="utf-8") as source:
            data = json.load(source)
        _reject_incomplete_json_fragment(data)
        return _with_expected_counts(data, fixture=data.get("meta", {}).get("tipo") == "fixture_tecnica")
    if path.suffix.lower() not in {".xlsx", ".xlsm"}:
        raise ValueError("Formato non supportato: usare .json, .xlsx o .xlsm")
    workbook = load_workbook(path, data_only=True, read_only=True)
    native_sheets = {"Programma Lezioni", "Percorso MVP", "Grammatica", "Vocabolario", "Comunicazione", "Liste"}
    if native_sheets.issubset(workbook.sheetnames):
        return _load_programma_workbook(workbook)
    required = {"Liste", "Lezioni", "Sezioni", "Quiz"}
    missing = required - set(workbook.sheetnames)
    if missing:
        raise ValueError(f"Fogli Excel mancanti: {', '.join(sorted(missing))}")
    lists = defaultdict(list)
    for row in _sheet_rows(workbook["Liste"]):
        lists[str(row["categoria"]).lower()].append({"code": str(row["code"]), "nome": str(row["nome"])})
    lessons = []
    for row in _sheet_rows(workbook["Lezioni"]):
        normalized = dict(row)
        normalized["competenze"] = _json_cell(row.get("competenze"), [])
        normalized["errori_tipici"] = _json_cell(row.get("errori_tipici"), [])
        lessons.append(normalized)
    sections = []
    for row in _sheet_rows(workbook["Sezioni"]):
        row["contenuto"] = _json_cell(row.get("contenuto"), {})
        sections.append(row)
    questions_by_quiz = defaultdict(list)
    for row in _sheet_rows(workbook["Quiz"]):
        key = (row["lezione_id"], row["modalita"])
        questions_by_quiz[key].append({
            "ordine": row["ordine"], "tipo": row["tipo"], "testo": row["testo"],
            "opzioni": _json_cell(row.get("opzioni"), []), "risposta_corretta": row["risposta_corretta"],
            "spiegazione": row["spiegazione"],
        })
    quizzes = [{"lezione_id": key[0], "modalita": key[1], "titolo": f"{key[1].title()}", "quesiti": value} for key, value in questions_by_quiz.items()]
    return _with_expected_counts({
        "liste": dict(lists), "lezioni": lessons,
        "sezioni": sections, "quiz": quizzes,
        "meta": {"formato": "excel_normalizzato"},
    })


def collect_source_structure_errors(data):
    errors = []
    audio_fields = _audio_field_paths(data)
    if audio_fields:
        errors.append(f"Campi audio non ammessi: {', '.join(audio_fields)}")
    for key in LOOKUP_MODELS:
        if key not in data.get("liste", {}):
            errors.append(f"Lista lookup mancante: {key}")
    lessons = data.get("lezioni", [])
    if not lessons:
        errors.append("Nessuna lezione nel file sorgente")
    lookup_codes = {
        key: {str(item["code"]) for item in data.get("liste", {}).get(key, [])}
        for key in LOOKUP_MODELS
    }
    if lookup_codes["area"] != SUPPORTED_AREAS:
        errors.append(
            "Le aree della fonte devono essere esclusivamente GRA, VOC e COM; "
            f"trovate: {', '.join(sorted(lookup_codes['area'])) or 'nessuna'}"
        )
    lookup_fields = {
        "area": "area", "tipologia": "tipologia", "livello": "livello",
        "difficolta": "difficolta", "stato": "stato",
    }
    orders = []
    mvp_orders = []
    for lesson in lessons:
        missing_fields = sorted(key for key in REQUIRED_LESSON_FIELDS if lesson.get(key) in (None, ""))
        if missing_fields:
            errors.append(f"{lesson.get('id', '<senza id>')}: campi obbligatori mancanti: {', '.join(missing_fields)}")
        for key, field in lookup_fields.items():
            value = lesson.get(field)
            if value is not None and str(value) not in lookup_codes[key]:
                errors.append(f"{lesson.get('id')}: valore {field} inesistente: {value}")
        if lesson.get("area") not in AREA_SECTION_COUNTS:
            errors.append(f"{lesson.get('id')}: area non supportata")
        if isinstance(lesson.get("ordine_percorso"), int):
            orders.append(lesson["ordine_percorso"])
            if not 1 <= lesson["ordine_percorso"] <= CATALOG_LESSON_COUNT:
                errors.append(f"{lesson.get('id')}: ordine_percorso fuori intervallo 1..98")
        if lesson.get("ordine_mvp") is not None:
            mvp_orders.append(lesson["ordine_mvp"])

    if sorted(orders) != list(range(1, len(lessons) + 1)):
        errors.append(f"ordine_percorso deve essere una sequenza unica 1..{len(lessons)}")
    if sorted(mvp_orders) != list(range(1, len(mvp_orders) + 1)):
        errors.append(f"ordine_mvp deve essere una sequenza unica 1..{len(mvp_orders)}")
    expected_lessons = data.get("meta", {}).get("catalogo_atteso")
    expected_mvp = data.get("meta", {}).get("mvp_atteso")
    if expected_lessons is not None and len(lessons) != expected_lessons:
        errors.append(f"Catalogo incompleto: attese {expected_lessons} lezioni, trovate {len(lessons)}")
    if expected_mvp is not None and len(mvp_orders) != expected_mvp:
        errors.append(f"Percorso MVP incompleto: attese {expected_mvp} lezioni, trovate {len(mvp_orders)}")

    lesson_ids = {row["id"] for row in lessons}
    section_counts = defaultdict(int)
    for section in data.get("sezioni", []):
        if section["lezione_id"] not in lesson_ids:
            errors.append(f"Sezione riferita a lezione inesistente: {section['lezione_id']}")
        section_counts[section["lezione_id"]] += 1
    for lesson in lessons:
        expected = AREA_SECTION_COUNTS.get(lesson.get("area"))
        if expected is None:
            continue
        if section_counts[lesson["id"]] != expected:
            errors.append(f"{lesson['id']}: attese {expected} sezioni, trovate {section_counts[lesson['id']]}")

    for quiz in data.get("quiz", []):
        if quiz["lezione_id"] not in lesson_ids:
            errors.append(f"Quiz riferito a lezione inesistente: {quiz['lezione_id']}")
        questions = quiz.get("quesiti", [])
        if quiz["modalita"] == StrutturaQuiz.FINALE and not 8 <= len(questions) <= 10:
            errors.append(f"{quiz['lezione_id']}: il quiz finale deve avere 8-10 quesiti")
        for question in questions:
            if question["tipo"] not in {QuesitoFinale.SCELTA_MULTIPLA, QuesitoFinale.COMPLETAMENTO}:
                errors.append(f"Tipo quesito non valido: {question['tipo']}")
            if question["tipo"] == QuesitoFinale.SCELTA_MULTIPLA and question["risposta_corretta"] not in question.get("opzioni", []):
                errors.append("La risposta corretta deve essere presente nelle opzioni")
    return errors


def validate_source(data):
    structure_errors = collect_source_structure_errors(data)
    if structure_errors:
        raise ValueError("Fonte non valida:\n- " + "\n- ".join(structure_errors))


def source_report(data):
    lessons = data.get("lezioni", [])
    mvp_ids = {row["id"] for row in lessons if row.get("ordine_mvp") is not None}
    errors = collect_source_structure_errors(data)
    warnings = []
    published_count = sum(row.get("stato") == "PUBBLICATA" and row.get("ordine_mvp") is not None for row in lessons)
    if not published_count:
        warnings.append("Nessuna lezione MVP ha stato PUBBLICATA")
    if not data.get("quiz"):
        warnings.append("Il file sorgente non contiene quesiti o quiz importabili")
    todo_sections = sum(str(section.get("contenuto", {}).get("todo", "")).startswith("TODO_FONTE:") for section in data.get("sezioni", []))
    if todo_sections:
        warnings.append(f"{todo_sections} sezioni attendono contenuti definitivi (TODO_FONTE)")
    if data.get("meta", {}).get("mvp_normalizzato"):
        warnings.append(
            "Applicato aggiornamento MVP dichiarato: GRA-A1-008 inserita all'ordine 11; "
            "gli ordini successivi sono stati incrementati"
        )
    return {
        "valido": not errors,
        "formato": data.get("meta", {}).get("formato", "normalizzato"),
        "conteggi": {
            "lezioni": len(lessons), "lezioni_mvp": len(mvp_ids), "lezioni_mvp_pubblicate": published_count,
            "sezioni": len(data.get("sezioni", [])),
            "sezioni_todo": todo_sections, "quiz": len(data.get("quiz", [])),
        },
        "errori": errors,
        "avvisi": warnings,
    }


@transaction.atomic
def import_content(path):
    data = load_source(path)
    validate_source(data)
    for key, model in LOOKUP_MODELS.items():
        source_codes = []
        for item in data["liste"][key]:
            code = str(item["code"])
            source_codes.append(code)
            model.objects.update_or_create(code=code, defaults={"nome": item["nome"]})

    source_ids = []
    for row in data["lezioni"]:
        source_ids.append(row["id"])
        defaults = {key: row.get(key, "") for key in (
            "nome", "descrizione", "categoria", "ordine_percorso", "obiettivo_didattico", "competenze",
            "durata_min", "errori_tipici", "ordine_mvp",
        )}
        defaults.update({
            "area_id": row["area"], "tipologia_id": row["tipologia"], "livello_id": row["livello"],
            "difficolta_id": row["difficolta"], "stato_id": row["stato"],
        })
        Lezione.objects.update_or_create(id=row["id"], defaults=defaults)

    Lezione.objects.exclude(id__in=source_ids).delete()
    StrutturaLezione.objects.all().delete()
    StrutturaLezione.objects.bulk_create([StrutturaLezione(
        lezione_id=row["lezione_id"], ordine=row["ordine"], tipo_sezione=row["tipo_sezione"],
        contenuto=row["contenuto"], formato_web=row.get("formato_web", "testo"),
    ) for row in data.get("sezioni", [])])
    StrutturaQuiz.objects.all().delete()
    for row in data.get("quiz", []):
        quiz = StrutturaQuiz.objects.create(lezione_id=row["lezione_id"], modalita=row["modalita"], titolo=row["titolo"])
        # I quesiti finiscono nella tabella della propria modalita'.
        model = QuesitoGuidato if row["modalita"] == StrutturaQuiz.GUIDATO else QuesitoFinale
        model.objects.bulk_create([model(quiz=quiz, **question) for question in row.get("quesiti", [])])
    for key, model in LOOKUP_MODELS.items():
        source_codes = [str(item["code"]) for item in data["liste"][key]]
        model.objects.exclude(code__in=source_codes).delete()
    return {"lezioni": len(source_ids)}
