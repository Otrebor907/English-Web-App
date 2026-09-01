# Dal file Excel a Neon — il percorso completo di una lezione

> **Cosa copre.** Tutto il lato backend dell'importazione: che cosa viene letto dal
> workbook, in quale variabile Python finisce, come quella variabile cambia forma a
> ogni passaggio, e quali istruzioni SQL arrivano infine al database Neon.
>
> **Lezione campione.** `GRA-A1-003 — Il verbo to be: forma affermativa`, seguita
> dalla cella Excel fino alla riga di tabella.
>
> **I valori riportati non sono di esempio: sono stati catturati eseguendo davvero
> il codice** su `programma_lezioni_inglese_no_audio.xlsx`. Il SQL è quello realmente
> emesso da Django, registrato con `CaptureQueriesContext`. In fondo trovi
> [come rifare la traccia](#appendice--come-riprodurre-questa-traccia) da solo.
>
> File di riferimento: [backend/learning/importer.py](../backend/learning/importer.py),
> 391 righe. I numeri di riga citati sono quelli attuali.

---

## Indice

1. [La mappa in una figura](#1-la-mappa-in-una-figura)
2. [Il punto di partenza: il file Excel](#2-il-punto-di-partenza-il-file-excel)
3. [Fase 0 — `load_source`: riconoscere la fonte](#3-fase-0--load_source-riconoscere-la-fonte)
4. [Fase 1 — `_load_programma_workbook`: costruire il dizionario](#4-fase-1--_load_programma_workbook-costruire-il-dizionario)
   - [1A. `area_codes`](#1a-area_codes--il-vocabolario-dei-codici)
   - [1B. `lists`](#1b-lists--le-cinque-tabelle-dimensione)
   - [1C. `mvp`](#1c-mvp--gli-ordini-del-percorso)
   - [1D. `lessons`](#1d-lessons--il-cuore)
   - [1E. `templates`](#1e-templates--lo-scheletro-delle-pagine)
   - [1F. `sections`](#1f-sections--la-moltiplicazione)
   - [1G. `data`](#1g-data--il-dizionario-finale)
5. [Fase 2 — la validazione](#5-fase-2--la-validazione)
6. [Fase 3 — `import_content`: la scrittura su Neon](#6-fase-3--import_content-la-scrittura-su-neon)
7. [Che cosa c'è su Neon alla fine](#7-che-cosè-su-neon-alla-fine)
8. [Che cosa manca ancora, e chi lo porta](#8-che-cosa-manca-ancora-e-chi-lo-porta)
9. [Appendice — come riprodurre questa traccia](#appendice--come-riprodurre-questa-traccia)

---

## 1. La mappa in una figura

```
  programma_lezioni_inglese_no_audio.xlsx          ← 6 fogli
                    │
                    │  openpyxl
                    ▼
   ┌──────────────────────────────────────┐
   │  load_source(path)          riga 213 │  smista: .json o workbook?
   └──────────────────┬───────────────────┘
                      ▼
   ┌──────────────────────────────────────┐
   │  _load_programma_workbook   riga 100 │  costruisce 7 variabili in cascata
   │                                      │
   │   area_codes ──┐                     │
   │   lists        │                     │
   │   mvp ─────────┼──► lessons ──┐      │
   │   templates ───────────────────┼──► sections
   └──────────────────┬───────────────────┘
                      ▼
              data = {liste, lezioni, sezioni, quiz, meta}     ← UN dizionario
                      │
   ┌──────────────────┴───────────────────┐
   │  validate_source            riga 313 │  ~15 invarianti; se una salta, si ferma
   └──────────────────┬───────────────────┘
                      ▼
   ┌──────────────────────────────────────┐
   │  import_content             riga 351 │  @transaction.atomic
   │  741 query SQL in UNA transazione    │
   └──────────────────┬───────────────────┘
                      ▼
        Neon Postgres 17 — English-web-app
        dim_* · learning_lezione · struttura_lezione · struttura_quiz*
```

Il punto da tenere a mente per tutto il documento: **esiste un solo oggetto al centro**,
il dizionario `data`. Ogni funzione o lo costruisce, o lo ispeziona, o lo svuota nel
database. Non c'è una quarta cosa.

```python
data = {
    "liste":   {...},   # dict con 5 chiavi   → le tabelle dimensione
    "lezioni": [...],   # list di 98 dict     → learning_lezione
    "sezioni": [...],   # list di 824 dict    → struttura_lezione
    "quiz":    [],      # list vuota          → struttura_quiz (nessuno, dal workbook)
    "meta":    {...},   # dict con 6 chiavi   → non finisce nel database
}
```

---

## 2. Il punto di partenza: il file Excel

Il workbook ha **6 fogli**, tutti e sei obbligatori. Il file ne aveva 13 fino al
31/08/2026: gli altri 7 erano documentazione che nessuna riga di codice leggeva e sono
stati rimossi (vedi [Logica_Didattica.md](Logica_Didattica.md)).

| Foglio | Che cosa contiene | Chi lo legge |
| --- | --- | --- |
| `Programma Lezioni` | 98 righe, una per lezione, 17 colonne | `lessons` |
| `Percorso MVP` | 28 righe con l'ordine del percorso ridotto | `mvp` |
| `Liste` | i valori ammessi per le 5 lookup + la mappa area→codice | `lists`, `area_codes` |
| `Grammatica` | il modello di pagina: 9 sezioni | `templates["GRA"]` |
| `Vocabolario` | il modello di pagina: 7 sezioni | `templates["VOC"]` |
| `Comunicazione` | il modello di pagina: 8 sezioni | `templates["COM"]` |

### La riga di GRA-A1-003

Nel foglio `Programma Lezioni` le prime tre righe sono decorative (titolo, sottotitolo,
riga vuota): **le intestazioni stanno alla riga 4**, i dati partono dalla 5. La nostra
lezione è alla **riga 7**.

| Colonna | Cella | Valore |
| --- | --- | --- |
| 1 | A7 | `GRA-A1-003` |
| 2 | B7 | `Grammatica` |
| 3 | C7 | `Regola ed esercizi` |
| 4 | D7 | `Il verbo to be: forma affermativa` |
| 5 | E7 | `Regola spiegata in parole semplici, strutture (affermativa, negativa, interrogativa), esempi con traduzione, confronto con l'italiano ed esercizi progressivi.` |
| 6 | F7 | `A1` |
| 7 | G7 | `Bassa` |
| 8 | H7 | `3` |
| 9 | I7 | `GRA-A1-002` ← **non letta** |
| 10 | J7 | `Coniugare to be al presente e usarlo per età, nazionalità, professione e stati.` |
| 11 | K7 | `Grammatica, Lettura` |
| 12 | L7 | `12` |
| 13 | M7 | `GRA-A1-002` ← **non letta** |
| 14 | N7 | `GRA-A1-004` ← **non letta** |
| 15 | O7 | `«I have 25 years» invece di «I am 25»; «I am agree» invece di «I agree».` |
| 16 | P7 | `Da sviluppare (MVP)` |
| 17 | Q7 | `Il verbo to be` |
| 18 | R7 | `RIEPILOGO` ← **fuori dal taglio** |

Le colonne 9, 13 e 14 vengono lette da openpyxl ma **mai usate**: erano il grafo dei
prerequisiti, eliminato con la migration `0008`. La colonna 18 è un riquadro
statistico appoggiato a fianco della tabella, escluso dal taglio a 17 colonne.

---

## 3. Fase 0 — `load_source`: riconoscere la fonte

```python
# importer.py, riga 213
def load_source(path):
    path = Path(path)
    if path.suffix.lower() == ".json":                      # ─── ramo A
        with path.open(encoding="utf-8") as source:
            data = json.load(source)
        _reject_incomplete_json_fragment(data)
        return _with_expected_counts(data, fixture=...)
    if path.suffix.lower() not in {".xlsx", ".xlsm"}:
        raise ValueError("Formato non supportato: usare .json, .xlsx o .xlsm")
    workbook = load_workbook(path, data_only=True, read_only=True)
    missing = NATIVE_SHEETS - set(workbook.sheetnames)      # ─── ramo B
    if missing:
        raise ValueError(f"Fogli Excel mancanti: {', '.join(sorted(missing))}. ...")
    return _load_programma_workbook(workbook)
```

Due rami soltanto. **Ramo A**, il JSON, serve alle fixture dei test
(`fixtures/contenuti_minimi.json`, usato da cinque file di test). **Ramo B** è il nostro.

Un terzo ramo — un formato Excel «normalizzato» con fogli `Liste`/`Lezioni`/`Sezioni`/`Quiz`
e JSON dentro le celle — è stato rimosso il 01/09/2026: nessun file lo usava e nessun
test lo esercitava.

Nota sui due parametri di `load_workbook`:

- `data_only=True` — restituisce il **risultato** delle formule, non la formula. Il
  workbook ne ha 13 (`=COUNTA(...)` nei riquadri di riepilogo), tutte fuori dal
  perimetro letto.
- `read_only=True` — modalità a flusso, non carica l'intero file in memoria.

Se il file non ha i sei fogli, l'errore nomina esattamente quelli che mancano:

```
ValueError: Fogli Excel mancanti: Liste, Percorso MVP.
Il file deve essere il workbook del programma, con i fogli: Comunicazione,
Grammatica, Liste, Percorso MVP, Programma Lezioni, Vocabolario
```

---

## 4. Fase 1 — `_load_programma_workbook`: costruire il dizionario

La funzione è lunga 100 righe e sembra un muro. In realtà costruisce **sette variabili
in un ordine obbligato**, perché ognuna dipende dalle precedenti:

```
riga 105   area_codes  ─────────┐
riga 121   lists                │  serve a lessons
riga 165   mvp         ─────────┤
riga 190   lessons     ◄────────┘
riga 239   templates   ─────────┐
riga 256   sections    ◄────────┘  serve templates + lessons
riga 260   return {...}
```

Leggila partendo dal `return` alla riga 190: ti dice che cosa deve produrre, e a quel
punto ogni paragrafo diventa «ah, questo riempie quella chiave».

### 1A. `area_codes` — il vocabolario dei codici

```python
# righe 102-105
area_codes = {}
for row in workbook["Liste"].iter_rows(min_row=16, max_row=18, min_col=1, max_col=2, values_only=True):
    if row[0] and row[1]:
        area_codes[str(row[0])] = str(row[1])
```

Legge un blocchetto di **tre righe** in fondo al foglio `Liste`, sotto l'intestazione
«Codici ID per area». Non usa `_sheet_rows_at` perché non è una tabella con
intestazioni: sono due colonne nude.

**Valore prodotto:**

```python
area_codes = {
    "Grammatica":    "GRA",
    "Vocabolario":   "VOC",
    "Comunicazione": "COM",
}
```

Tre coppie. È il dizionario che più avanti trasformerà il `Grammatica` scritto in B7
nel `GRA` che finisce nel database.

### 1B. `lists` — le cinque tabelle dimensione

```python
# righe 107-124
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
```

`_sheet_rows_at(sheet, 4, 8, max_row=10)` significa: intestazioni alla riga 4, leggi
fino alla colonna 8 e alla riga 10. Il limite di riga serve perché sotto la riga 10 il
foglio riparte con un blocco diverso (i codici area del paragrafo precedente).

**Le righe grezze in ingresso** — colonne parallele, con buchi perché le liste hanno
lunghezze diverse:

```python
righe_liste[0] = {'Area Didattica': 'Grammatica',    'Tipologia Lezione': 'Regola ed esercizi', 'Livello Linguistico': 'A1', 'Difficoltà': 'Bassa', 'Stato della Lezione': 'Da sviluppare',       ...}
righe_liste[1] = {'Area Didattica': 'Vocabolario',   'Tipologia Lezione': 'Lessico tematico',   'Livello Linguistico': 'A2', 'Difficoltà': 'Media', 'Stato della Lezione': 'Da sviluppare (MVP)', ...}
righe_liste[2] = {'Area Didattica': 'Comunicazione', 'Tipologia Lezione': 'Dialogo',            'Livello Linguistico': 'B1', 'Difficoltà': 'Alta',  'Stato della Lezione': 'In sviluppo',         ...}
righe_liste[3] = {'Area Didattica': None,            'Tipologia Lezione': 'Produzione Guidata', 'Livello Linguistico': 'B2', 'Difficoltà': None,    'Stato della Lezione': 'In revisione',        ...}
righe_liste[4] = {'Area Didattica': None,            'Tipologia Lezione': 'Produzione Libera',  'Livello Linguistico': 'C1', 'Difficoltà': None,    'Stato della Lezione': 'Completata',          ...}
righe_liste[5] = {'Area Didattica': None,            'Tipologia Lezione': None,                 'Livello Linguistico': 'C2', 'Difficoltà': None,    'Stato della Lezione': 'Pubblicata',          ...}
```

Il `if not value: continue` è ciò che salta i `None`. Il `seen` evita i duplicati:
il ciclo legge per righe, ma costruisce cinque liste indipendenti.

**Tre regole di trasformazione diverse**, tutte in quell'espressione condizionale:

| Chiave | Regola | Esempio |
| --- | --- | --- |
| `area` | passa da `area_codes` | `Grammatica` → `GRA` |
| `livello`, `difficolta` | **nessuna** trasformazione: il valore è già il codice | `A1` → `A1`, `Bassa` → `Bassa` |
| `tipologia`, `stato` | `_code()` | `Da sviluppare (MVP)` → `DA_SVILUPPARE_MVP` |

**Valore prodotto:**

```python
lists["area"] = [
    {'code': 'GRA', 'nome': 'Grammatica'},
    {'code': 'VOC', 'nome': 'Vocabolario'},
    {'code': 'COM', 'nome': 'Comunicazione'},
]
lists["tipologia"] = [
    {'code': 'REGOLA_ED_ESERCIZI', 'nome': 'Regola ed esercizi'},
    {'code': 'LESSICO_TEMATICO',   'nome': 'Lessico tematico'},
    {'code': 'DIALOGO',            'nome': 'Dialogo'},
    {'code': 'PRODUZIONE_GUIDATA', 'nome': 'Produzione Guidata'},
    {'code': 'PRODUZIONE_LIBERA',  'nome': 'Produzione Libera'},
]
lists["livello"] = [
    {'code': 'A1', 'nome': 'A1'}, {'code': 'A2', 'nome': 'A2'}, {'code': 'B1', 'nome': 'B1'},
    {'code': 'B2', 'nome': 'B2'}, {'code': 'C1', 'nome': 'C1'}, {'code': 'C2', 'nome': 'C2'},
]
lists["difficolta"] = [
    {'code': 'Bassa', 'nome': 'Bassa'}, {'code': 'Media', 'nome': 'Media'}, {'code': 'Alta', 'nome': 'Alta'},
]
lists["stato"] = [
    {'code': 'DA_SVILUPPARE',     'nome': 'Da sviluppare'},
    {'code': 'DA_SVILUPPARE_MVP', 'nome': 'Da sviluppare (MVP)'},
    {'code': 'IN_SVILUPPO',       'nome': 'In sviluppo'},
    {'code': 'IN_REVISIONE',      'nome': 'In revisione'},
    {'code': 'COMPLETATA',        'nome': 'Completata'},
    {'code': 'PUBBLICATA',        'nome': 'Pubblicata'},
]
```

Totale **23 voci** su cinque liste. Diventeranno 23 righe su cinque tabelle Postgres.

#### Come funziona `_code()`

```python
# riga 48
def _code(value):
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Z0-9]+", "_", normalized.upper()).strip("_")
```

Tre passaggi su `"Da sviluppare (MVP)"`:

```
1. NFKD + encode/decode ascii  →  "Da sviluppare (MVP)"     (qui nulla da spogliare)
2. .upper()                    →  "DA SVILUPPARE (MVP)"
3. re.sub + strip              →  "DA_SVILUPPARE_MVP"
```

Il passaggio 1 conta su parole accentate: `Difficoltà` diventerebbe `DIFFICOLTA`, senza
accento. Serve perché un identificatore accentato in Postgres andrebbe messo tra
virgolette in ogni query.

### 1C. `mvp` — gli ordini del percorso

```python
# righe 126-131
mvp = {}
for row in _sheet_rows_at(workbook["Percorso MVP"], 4, 9):
    lesson_id = row.get("ID Lezione")
    if not lesson_id or not isinstance(row.get("Ordine MVP"), (int, float)):
        continue
    mvp[str(lesson_id)] = {"ordine_mvp": int(row["Ordine MVP"])}
```

Il doppio controllo serve a scartare le righe di riepilogo in fondo al foglio, che hanno
un testo nella colonna del titolo ma non un numero in `Ordine MVP`.

**Valore prodotto — 28 voci:**

```python
mvp = {
    'GRA-A1-001': {'ordine_mvp': 1},
    'GRA-A1-002': {'ordine_mvp': 2},
    'GRA-A1-003': {'ordine_mvp': 3},      # ← la nostra
    'GRA-A1-004': {'ordine_mvp': 4},
    'COM-A1-001': {'ordine_mvp': 5},
    'VOC-A1-001': {'ordine_mvp': 6},
    'GRA-A1-005': {'ordine_mvp': 7},
    'GRA-A1-006': {'ordine_mvp': 8},
    'VOC-A1-002': {'ordine_mvp': 9},
    'GRA-A1-007': {'ordine_mvp': 10},
    'GRA-A1-008': {'ordine_mvp': 11},
    'GRA-A1-009': {'ordine_mvp': 12},
    'VOC-A1-003': {'ordine_mvp': 13},
    ...                                    # fino a 29
}
```

#### La riga che mancava — e non manca più

Fino al 01/09/2026 il foglio aveva **28 righe**: `GRA-A1-008` non c'era, benché la
lezione esistesse nel catalogo (riga 15 di `Programma Lezioni`, «Dimostrativi: this,
that, these, those») e fosse dichiarata prerequisito di `GRA-A1-009`. Il parser
rimediava da solo, inserendo la voce mancante all'ordine 11 e incrementando i
successivi, e ne dava avviso a ogni validazione.

Quel codice è stato **rimosso**, e la riga è stata aggiunta al workbook: il foglio ne
ha 29, numerate 1..29. La regola che ne resta è più semplice da tenere a mente:

> il parser legge, non ripara.

Se il foglio tornasse a 28 righe, `MVP_LESSON_COUNT = 29` farebbe fallire la
validazione con `Percorso MVP incompleto: attese 29 lezioni, trovate 28`. L'anomalia
viene segnalata, non tamponata.

### 1D. `lessons` — il cuore

```python
# righe 142-166
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
```

I due argomenti `4, 17` sono posizionali: `header_row=4` e `max_column=17`.

#### Passaggio 1 — la riga grezza

`_sheet_rows_at` restituisce **una lista di 98 dizionari**. Le chiavi sono le
intestazioni della riga 4, alla lettera, accenti e spazi compresi. Il terzo elemento è
la nostra lezione:

```python
righe[2] = {
    'ID Lezione': 'GRA-A1-003',
    'Area Didattica': 'Grammatica',
    'Tipologia Lezione': 'Regola ed esercizi',
    'Nome Lezione': 'Il verbo to be: forma affermativa',
    'Breve Descrizione': "Regola spiegata in parole semplici, strutture (affermativa, "
                         "negativa, interrogativa), esempi con traduzione, confronto con "
                         "l'italiano ed esercizi progressivi.",
    'Livello Linguistico': 'A1',
    'Difficoltà': 'Bassa',
    'Ordine nel Percorso': 3,                # int: openpyxl legge i numeri come numeri
    'Prerequisiti': 'GRA-A1-002',            # presente ma mai usata
    'Obiettivo Didattico': 'Coniugare to be al presente e usarlo per età, nazionalità, '
                           'professione e stati.',
    'Competenze Allenate': 'Grammatica, Lettura',   # una stringa sola, con la virgola dentro
    'Durata Stimata (min)': 12,
    'Lezione Precedente': 'GRA-A1-002',      # presente ma mai usata
    'Lezione Successiva': 'GRA-A1-004',      # presente ma mai usata
    'Errori Tipici degli Italiani': '«I have 25 years» invece di «I am 25»; '
                                    '«I am agree» invece di «I agree».',
    'Stato della Lezione': 'Da sviluppare (MVP)',
    'Categoria': 'Il verbo to be',
}
```

Diciassette chiavi, esattamente le 17 colonne del taglio. Niente `RIEPILOGO`.

#### Passaggio 2 — il dizionario normalizzato

```python
lessons[2] = {
    'id': 'GRA-A1-003',
    'area': 'GRA',                                     # ← area_codes['Grammatica']
    'tipologia': 'REGOLA_ED_ESERCIZI',                 # ← _code('Regola ed esercizi')
    'nome': 'Il verbo to be: forma affermativa',
    'descrizione': 'Regola spiegata in parole semplici, strutture (affermativa, negativa, '
                   "interrogativa), esempi con traduzione, confronto con l'italiano ed "
                   'esercizi progressivi.',
    'categoria': 'Il verbo to be',
    'livello': 'A1',
    'difficolta': 'Bassa',
    'ordine_percorso': 3,
    'obiettivo_didattico': 'Coniugare to be al presente e usarlo per età, nazionalità, '
                           'professione e stati.',
    'competenze': ['Grammatica', 'Lettura'],           # ← _split_list: str → list
    'durata_min': 12,
    'errori_tipici': ['«I have 25 years» invece di «I am 25»; '
                      '«I am agree» invece di «I agree».'],   # ← avvolta in una lista
    'stato': 'DA_SVILUPPARE_MVP',                      # ← _code('Da sviluppare (MVP)')
    'ordine_mvp': 3,                                   # ← NON dalla riga: da mvp['GRA-A1-003']
}
```

#### I tipi Python, campo per campo

| Chiave | Tipo | Diventerà, su Postgres |
| --- | --- | --- |
| `id` | `str` | `varchar(32)`, chiave primaria |
| `area`, `tipologia`, `livello`, `difficolta`, `stato` | `str` | `varchar` **foreign key** (`area_id`, …) |
| `nome`, `descrizione`, `categoria`, `obiettivo_didattico` | `str` | `varchar` / `text` |
| `ordine_percorso`, `durata_min` | `int` | `integer` / `smallint` |
| `ordine_mvp` | `int` oppure `None` | `integer NULL`, con vincolo `UNIQUE` |
| `competenze`, `errori_tipici` | `list` | **`jsonb`** |

#### Le cinque trasformazioni, affiancate

```
'Area Didattica': 'Grammatica'             →  'area': 'GRA'
'Tipologia Lezione': 'Regola ed esercizi'  →  'tipologia': 'REGOLA_ED_ESERCIZI'
'Stato della Lezione': 'Da sviluppare (MVP)' → 'stato': 'DA_SVILUPPARE_MVP'
'Competenze Allenate': 'Grammatica, Lettura' → 'competenze': ['Grammatica', 'Lettura']
'Errori Tipici…': '«I have 25 years»…'      →  'errori_tipici': ['«I have 25 years»…']
```

E **tre chiavi spariscono**: `Prerequisiti`, `Lezione Precedente`, `Lezione Successiva`.
Il ciclo semplicemente non le legge.

#### Il caso `ordine_mvp: None`

29 lezioni su 98 hanno un ordine MVP; le altre 69 no. È il motivo dell'ultima espressione
del ciclo, `mvp_row["ordine_mvp"] if mvp_row else None`:

```python
{
  'id': 'GRA-A2-002',
  'nome': 'Past simple: verbi regolari',
  'ordine_percorso': 30,
  'stato': 'DA_SVILUPPARE',    # senza «(MVP)»: è lo stato di chi resta fuori
  'ordine_mvp': None,          # ← None in Python, NULL in Postgres
  ...
}
```

Quel `None` è ciò che, più a valle, tiene la lezione fuori dall'endpoint `/api/percorso/`,
che filtra con `ordine_mvp__isnull=False`.

#### Come funziona `_split_list()`

```python
# riga 53
def _split_list(value):
    if value in (None, "", "—") or str(value).strip().casefold() in {"nessuno", "nessuna"}:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]
```

Tratta quattro modi diversi di scrivere «vuoto» in un foglio Excel — cella vuota, stringa
vuota, trattino lungo, la parola «Nessuno» — e li riduce tutti alla lista vuota.

```
'Grammatica, Lettura'  →  ['Grammatica', 'Lettura']
'Nessuno'              →  []
'—'                    →  []
None                   →  []
```

### 1E. `templates` — lo scheletro delle pagine

```python
# righe 168-185
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
```

Il `break` (non `continue`) è deliberato: sotto la tabella del modello, il foglio riparte
con l'elenco delle lezioni dell'area, che non ha un numero nella colonna `Ordine`. Al
primo valore non numerico il ciclo si ferma.

**Il modello di Grammatica — 9 voci:**

| ordine | tipo_sezione | formato_sorgente (dal foglio) |
| --- | --- | --- |
| 1 | Obiettivo della lezione | Banner in evidenza |
| 2 | Regola e quando si usa | Testo + box evidenziato |
| 3 | Struttura | Tabella o schema |
| 4 | Esempi con traduzione | Card di esempio |
| 5 | Errori tipici degli italiani | Box confronto ❌/✅ |
| 6 | Confronto con forme simili | Tabella comparativa |
| 7 | Esercizio guidato | Quiz assistito |
| 8 | Esercizio finale | Quiz interattivo |
| 9 | Riepilogo e prossima lezione | Card + pulsante di navigazione |

`Vocabolario` ne ha 7, `Comunicazione` 8. Questi numeri sono scritti anche nel codice,
come contratto da verificare: `AREA_SECTION_COUNTS = {"GRA": 9, "VOC": 7, "COM": 8}` (riga 22).

**Qui nasce il segnaposto.** `"todo": f"TODO_FONTE: {row['Contenuto Previsto']}"` e
`"formato_web": "todo"`: il workbook descrive *che cosa andrà scritto*, non lo scrive.

### 1F. `sections` — la moltiplicazione

```python
# righe 186-189
sections = [
    {"lezione_id": lesson["id"], **section}
    for lesson in lessons for section in templates[lesson["area"]]
]
```

Una list comprehension a doppio `for`: ogni lezione viene moltiplicata per il modello
della sua area.

```
57 lezioni GRA × 9  =  513
17 lezioni VOC × 7  =  119
24 lezioni COM × 8  =  192
────────────────────────────
                       824 sezioni
```

**Le 9 sezioni di GRA-A1-003.** La prima, integrale:

```python
{
    'lezione_id': 'GRA-A1-003',
    'ordine': 1,
    'tipo_sezione': 'Obiettivo della lezione',
    'contenuto': {
        'titolo': 'Obiettivo della lezione',
        'todo': 'TODO_FONTE: Una frase concreta («Alla fine saprai dire cosa stai facendo '
                'in questo momento»).',
        'obiettivo_template': 'Dire subito cosa si saprà fare alla fine.',
        'formato_sorgente': 'Banner in evidenza',
    },
    'formato_web': 'todo',
}
```

La quinta, quella degli errori tipici:

```python
{
    'lezione_id': 'GRA-A1-003',
    'ordine': 5,
    'tipo_sezione': 'Errori tipici degli italiani',
    'contenuto': {
        'titolo': 'Errori tipici degli italiani',
        'todo': 'TODO_FONTE: Frase sbagliata → frase corretta → perché '
                '(es. «I have 25 years» → «I am 25»).',
        'obiettivo_template': "Prevenire i calchi dall'italiano.",
        'formato_sorgente': 'Box confronto ❌/✅',
    },
    'formato_web': 'todo',
}
```

E tutte e nove in forma compatta:

```
ordine=1  formato_web=todo  Obiettivo della lezione
ordine=2  formato_web=todo  Regola e quando si usa
ordine=3  formato_web=todo  Struttura
ordine=4  formato_web=todo  Esempi con traduzione
ordine=5  formato_web=todo  Errori tipici degli italiani
ordine=6  formato_web=todo  Confronto con forme simili
ordine=7  formato_web=todo  Esercizio guidato
ordine=8  formato_web=todo  Esercizio finale
ordine=9  formato_web=todo  Riepilogo e prossima lezione
```

Nove caselle vuote, etichettate. **Nessun contenuto didattico.**

### 1G. `data` — il dizionario finale

```python
# righe 260-271
return {
    "liste": dict(lists), "lezioni": lessons,
    "sezioni": sections, "quiz": [],
    "meta": {
        "formato": "programma_lezioni",
        "catalogo_atteso": CATALOG_LESSON_COUNT,   # 98
        "mvp_atteso": MVP_LESSON_COUNT,            # 29
        "quiz_mancanti": True,
        "contenuti_sezioni_todo": True,
    },
}
```

**Valore prodotto:**

```
data['liste']    dict   len=5
data['lezioni']  list   len=98      ← GRA-A1-003 è all'indice 2
data['sezioni']  list   len=824
data['quiz']     list   len=0       ← zero: il workbook non contiene un solo quesito
data['meta']     dict   len=5
```

```python
data["meta"] = {
    'formato': 'programma_lezioni',
    'catalogo_atteso': 98,
    'mvp_atteso': 29,
    'quiz_mancanti': True,
    'contenuti_sezioni_todo': True,
}
```

`meta` non finisce nel database: serve al validatore per sapere che cosa aspettarsi, e
al report per produrre gli avvisi.

---

## 5. Fase 2 — la validazione

```python
# riga 313
def validate_source(data):
    structure_errors = collect_source_structure_errors(data)
    if structure_errors:
        raise ValueError("Fonte non valida:\n- " + "\n- ".join(structure_errors))
```

Il vero lavoro è in `collect_source_structure_errors` (riga 232), che **non solleva mai
eccezioni e non si ferma al primo problema**: accumula tutto in una lista e la restituisce.
È per questo che un file rotto ti mostra tutti i suoi errori in un colpo solo.

Due funzioni la vestono in modi diversi:

- **`validate_source`** — se la lista non è vuota, esplode. Usata da `import_content`.
- **`source_report`** (riga 319) — produce un referto con conteggi, errori **e avvisi**.
  Usata da `valida_contenuti`.

### I controlli che contano

| Controllo | Per GRA-A1-003 / per il file |
| --- | --- |
| Nessun campo il cui nome contenga «audio», a qualsiasi profondità | ✅ nessuno |
| Le aree devono essere esattamente `{GRA, VOC, COM}` | ✅ |
| Ogni lezione ha tutti i campi di `REQUIRED_LESSON_FIELDS` | ✅ 12 campi presenti |
| I valori di lookup esistono nelle liste | ✅ `GRA`, `REGOLA_ED_ESERCIZI`, `A1`, `Bassa`, `DA_SVILUPPARE_MVP` |
| `ordine_percorso` è una permutazione esatta di 1..98 | ✅ |
| `ordine_mvp` è una permutazione esatta di 1..29 | ✅ (dalle 29 righe del foglio) |
| Ogni lezione ha il numero di sezioni della sua area | ✅ 9 per GRA-A1-003 |
| Il quiz finale, se presente, ha 8–10 quesiti | — nessun quiz dal workbook |

**Esito reale sul workbook:**

```json
{
  "valido": true,
  "formato": "programma_lezioni",
  "conteggi": {
    "lezioni": 98, "lezioni_mvp": 29, "lezioni_mvp_pubblicate": 0,
    "sezioni": 824, "sezioni_todo": 824, "quiz": 0
  },
  "errori": []
}
```

con tre avvisi, tutti attesi: nessuna lezione MVP pubblicata, nessun quiz nella
fonte, 824 sezioni in attesa di contenuto.

---

## 6. Fase 3 — `import_content`: la scrittura su Neon

```python
# riga 350
@transaction.atomic
def import_content(path):
    data = load_source(path)      # produce il dizionario
    validate_source(data)         # controlla, o si ferma
    ...                           # scrive
```

Il decoratore `@transaction.atomic` è ciò che rende vera la frase
`IMPORT FALLITO — nessuna modifica salvata`: **tutte** le query stanno dentro un unico
`BEGIN … COMMIT`. Se qualcosa esplode alla query 700, Postgres annulla anche la prima.

### 6.1 — Le lookup

```python
for key, model in LOOKUP_MODELS.items():
    source_codes = []
    for item in data["liste"][key]:
        code = str(item["code"])
        source_codes.append(code)
        model.objects.update_or_create(code=code, defaults={"nome": item["nome"]})
```

`LOOKUP_MODELS` (riga 14) lega le cinque chiavi di `data["liste"]` ai cinque modelli:

```python
{"area": Area, "tipologia": Tipologia, "livello": Livello,
 "difficolta": Difficolta, "stato": StatoLezione}
```

**SQL reale, primo import su database vuoto:**

```sql
SELECT "dim_area_lezione"."code", "dim_area_lezione"."nome"
  FROM "dim_area_lezione" WHERE "dim_area_lezione"."code" = 'GRA' LIMIT 21;
INSERT INTO "dim_area_lezione" ("code", "nome") VALUES ('GRA', 'Grammatica');
INSERT INTO "dim_area_lezione" ("code", "nome") VALUES ('VOC', 'Vocabolario');
INSERT INTO "dim_area_lezione" ("code", "nome") VALUES ('COM', 'Comunicazione');
```

**Lo stesso comando, eseguito una seconda volta:**

```sql
UPDATE "dim_area_lezione" SET "nome" = 'Grammatica'    WHERE "dim_area_lezione"."code" = 'GRA';
UPDATE "dim_area_lezione" SET "nome" = 'Vocabolario'   WHERE "dim_area_lezione"."code" = 'VOC';
UPDATE "dim_area_lezione" SET "nome" = 'Comunicazione' WHERE "dim_area_lezione"."code" = 'COM';
```

**Questa è l'idempotenza, vista dal database.** `update_or_create` fa prima una `SELECT`:
se trova la riga aggiorna, se non la trova inserisce. Rieseguire l'import non duplica nulla.

### 6.2 — Le lezioni

```python
source_ids = []
for row in data["lezioni"]:
    source_ids.append(row["id"])
    defaults = {key: row.get(key, "") for key in (
        "nome", "descrizione", "categoria", "ordine_percorso", "obiettivo_didattico",
        "competenze", "durata_min", "errori_tipici", "ordine_mvp",
    )}
    defaults.update({
        "area_id": row["area"], "tipologia_id": row["tipologia"], "livello_id": row["livello"],
        "difficolta_id": row["difficolta"], "stato_id": row["stato"],
    })
    Lezione.objects.update_or_create(id=row["id"], defaults=defaults)
```

Nota il suffisso `_id`: `area_id="GRA"` assegna direttamente la chiave esterna, senza
caricare l'oggetto `Area` dal database. Con `area=<oggetto>` Django avrebbe dovuto fare
una `SELECT` in più per ognuna delle 98 lezioni.

**Il SQL vero per la nostra lezione — primo import:**

```sql
INSERT INTO "learning_lezione" (
    "id", "area_id", "tipologia_id", "nome", "descrizione", "categoria",
    "livello_id", "difficolta_id", "ordine_percorso", "obiettivo_didattico",
    "competenze", "durata_min", "errori_tipici", "stato_id", "ordine_mvp"
) VALUES (
    'GRA-A1-003',
    'GRA',
    'REGOLA_ED_ESERCIZI',
    'Il verbo to be: forma affermativa',
    'Regola spiegata in parole semplici, strutture (affermativa, negativa, interrogativa), esempi con traduzione, confronto con l''italiano ed esercizi progressivi.',
    'Il verbo to be',
    'A1',
    'Bassa',
    3,
    'Coniugare to be al presente e usarlo per età, nazionalità, professione e stati.',
    '["Grammatica", "Lettura"]',
    12,
    '["«I have 25 years» invece di «I am 25»; «I am agree» invece di «I agree»."]',
    'DA_SVILUPPARE_MVP',
    3
);
```

Tre cose da notare:

1. **`l''italiano`** — l'apostrofo raddoppiato: è Django che mette in sicurezza il valore
   contro la SQL injection. In produzione usa parametri legati, non interpolazione.
2. **`'["Grammatica", "Lettura"]'`** — la lista Python è diventata JSON. La colonna è
   `jsonb`: Postgres la conserva come struttura interrogabile, non come testo.
3. **`«` e `»`** — sono le virgolette basse `«` e `»`, serializzate da
   `json.dumps` con `ensure_ascii=True` (il default). Nel database il valore torna
   correttamente come `«I have 25 years»`.

**Lo stesso, al secondo import:** `SELECT` + `UPDATE` invece di `INSERT`.

### 6.3 — La potatura e le sezioni

```python
Lezione.objects.exclude(id__in=source_ids).delete()
StrutturaLezione.objects.all().delete()
StrutturaLezione.objects.bulk_create([...])
StrutturaQuiz.objects.all().delete()
```

Tre righe che meritano attenzione, in ordine crescente di pericolosità:

**`Lezione.objects.exclude(id__in=source_ids).delete()`** — cancella le lezioni che nel
workbook non ci sono più. Emette prima una `SELECT ... WHERE NOT (id IN ('GRA-A1-001',
'GRA-A1-002', … 98 valori))`. Nel nostro caso non trova nulla da cancellare, quindi
nessun `DELETE` viene eseguito.

**`StrutturaLezione.objects.all().delete()`** — nessun filtro:

```sql
DELETE FROM "struttura_lezione";
```

⚠️ **È la riga più pericolosa dell'intero file.** Cancella *tutte* le sezioni di *tutte* le
lezioni, comprese quelle pubblicate a mano dai brief markdown. Insieme alla riga gemella
su `StrutturaQuiz`, è il motivo per cui `importa_contenuti` da solo spubblica il lavoro
editoriale già fatto, e per cui esiste il comando `importa_in_sicurezza`.

**`bulk_create`** — le 824 sezioni non diventano 824 `INSERT`: Django le raggruppa in
lotti. Nella traccia su SQLite sono uscite **5 istruzioni** da circa 199 righe l'una:

```
INSERT #1: 199 righe,  58.771 caratteri
INSERT #2: 199 righe,  58.714 caratteri
INSERT #3: 199 righe,  58.586 caratteri
INSERT #4: 199 righe,  58.955 caratteri
INSERT #5:  28 righe,   8.288 caratteri
```

La dimensione del lotto dipende dal database (SQLite ha un limite sul numero di variabili
per istruzione; Postgres ne consente di più), quindi su Neon il numero di `INSERT` sarà
diverso — il meccanismo è lo stesso.

Ecco l'inizio del primo lotto, così vedi come una sezione arriva davvero a destinazione:

```sql
INSERT INTO "struttura_lezione" ("lezione_id", "ordine", "tipo_sezione", "contenuto", "formato_web")
VALUES ('GRA-A1-001', 1, 'Obiettivo della lezione',
        '{"titolo": "Obiettivo della lezione", "todo": "TODO_FONTE: Una frase concreta (...)", "obiettivo_template": "Dire subito cosa si saprà fare alla fine.", "formato_sorgente": "Banner in evidenza"}',
        'todo'),
       ('GRA-A1-001', 2, 'Regola e quando si usa', '{...}', 'todo'),
       ...
```

Il dizionario `contenuto` della sezione è diventato una colonna `jsonb`.

### 6.4 — Le lookup orfane

```python
for key, model in LOOKUP_MODELS.items():
    source_codes = [str(item["code"]) for item in data["liste"][key]]
    model.objects.exclude(code__in=source_codes).delete()
```

Ultimo passaggio, e **deve** stare in fondo: cancella i codici di lookup non più presenti
nella fonte. Se stesse all'inizio, tenterebbe di cancellare righe ancora referenziate
dalle lezioni e Postgres rifiuterebbe per violazione di chiave esterna (i modelli usano
`on_delete=models.PROTECT`).

### 6.5 — Il conto delle query

**Primo import su database vuoto: 741 query.**

| Verbo | Tabella | Quante |
| --- | --- | ---: |
| `SAVEPOINT` | — | 242 |
| `RELEASE` | — | 242 |
| `SELECT` | `learning_lezione` | 99 |
| `INSERT` | `learning_lezione` | 98 |
| `SELECT` | `dim_livello` | 7 |
| `SELECT` | `dim_stato_lezione` | 7 |
| `SELECT` | `dim_tipologia` | 6 |
| `INSERT` | `dim_livello` | 6 |
| `INSERT` | `dim_stato_lezione` | 6 |
| `INSERT` | `dim_tipologia` | 5 |
| `INSERT` | `struttura_lezione` | 5 |
| `SELECT` | `dim_area_lezione` | 4 |
| `SELECT` | `dim_difficolta_lezione` | 4 |
| `INSERT` | `dim_area_lezione` | 3 |
| `INSERT` | `dim_difficolta_lezione` | 3 |
| `BEGIN` | — | **1** |
| `DELETE` | `struttura_lezione` | 1 |
| `SELECT` | `struttura_quiz` | 1 |
| `COMMIT` | — | **1** |

Come leggere questa tabella:

- **Un solo `BEGIN` e un solo `COMMIT`.** Ecco `@transaction.atomic` visto dal database:
  741 query, una transazione.
- **242 `SAVEPOINT` e 242 `RELEASE`** = 2 per ciascuna delle 121 chiamate a
  `update_or_create` (23 lookup + 98 lezioni). Ogni `update_or_create` apre il proprio
  blocco atomico annidato, che su Postgres si traduce in un savepoint.
- **99 `SELECT` su `learning_lezione`** = 98 per le lezioni + 1 per la potatura finale.
- **`INSERT` su `learning_lezione`: 98, uno per lezione.** Non c'è `bulk_create` qui,
  perché `update_or_create` deve poter aggiornare le righe già presenti.

**Secondo import, con i dati già dentro: 499 query.** Spariscono i 242 savepoint delle
inserzioni e gli `INSERT` diventano `UPDATE`. Risultato finale identico: 98 lezioni.

```
primo import  (DB vuoto)  →  741 query  →  98 lezioni
secondo import            →  499 query  →  98 lezioni      ← nessun duplicato
```

---

## 7. Che cos'è su Neon alla fine

Progetto `English-web-app`, Postgres 17, regione `aws-eu-central-1`.

```
dim_area_lezione          3 righe     GRA → "Grammatica"
dim_tipologia             5 righe     REGOLA_ED_ESERCIZI → "Regola ed esercizi"
dim_livello               6 righe     A1 → "A1"
dim_difficolta_lezione    3 righe     Bassa → "Bassa"
dim_stato_lezione         6 righe     DA_SVILUPPARE_MVP → "Da sviluppare (MVP)"
        │
        │ (5 foreign key)
        ▼
learning_lezione         98 righe   ← GRA-A1-003 è una di queste
        │
        ├──< struttura_lezione     824 righe   (9 per GRA-A1-003, tutte TODO_FONTE)
        │
        └──< struttura_quiz          0 righe   ← il workbook non porta quiz
                 ├──< struttura_quiz_guidato    0
                 └──< struttura_quiz_finale     0
```

I nomi delle tabelle sono dichiarati esplicitamente in
[models.py](../backend/learning/models.py) con `db_table`, non generati da Django. Il
prefisso `dim_` è minuscolo di proposito: Postgres abbassa gli identificatori non
virgolettati, quindi `SELECT * FROM dim_livello` funziona senza virgolette.

**La riga di GRA-A1-003 in `learning_lezione`:**

| Colonna | Valore | Tipo Postgres |
| --- | --- | --- |
| `id` | `GRA-A1-003` | `varchar(32)` PK |
| `area_id` | `GRA` | `varchar` FK → `dim_area_lezione` |
| `tipologia_id` | `REGOLA_ED_ESERCIZI` | `varchar` FK |
| `nome` | `Il verbo to be: forma affermativa` | `varchar(200)` |
| `descrizione` | `Regola spiegata in parole semplici…` | `text` |
| `categoria` | `Il verbo to be` | `varchar(120)` |
| `livello_id` | `A1` | `varchar` FK |
| `difficolta_id` | `Bassa` | `varchar` FK |
| `ordine_percorso` | `3` | `integer` UNIQUE, vincolo 1..98 |
| `obiettivo_didattico` | `Coniugare to be al presente…` | `text` |
| `competenze` | `["Grammatica", "Lettura"]` | `jsonb` |
| `durata_min` | `12` | `smallint` |
| `errori_tipici` | `["«I have 25 years» invece di…"]` | `jsonb` |
| `stato_id` | `DA_SVILUPPARE_MVP` | `varchar` FK |
| `ordine_mvp` | `3` | `integer` NULL, UNIQUE |

### Come ci arrivano i dati, fisicamente

Non c'è nessuna API HTTP in mezzo. Django parla con Neon **sul protocollo nativo di
Postgres**, tramite `psycopg 3.2.9`, su TLS:

```
importer.py → Django ORM → psycopg → TCP/TLS porta 5432
            → ep-….c-5.eu-central-1.aws.neon.tech
```

La configurazione in [settings.py](../backend/config/settings.py) ha tre accorgimenti
specifici per Neon:

| Impostazione | Perché |
| --- | --- |
| `sslmode: require` | Neon accetta solo connessioni cifrate |
| `CONN_HEALTH_CHECKS: True` | Neon sospende il compute dopo 5 minuti di inattività; senza il controllo, Django riuserebbe una connessione ormai chiusa |
| `DISABLE_SERVER_SIDE_CURSORS: True` | il pooler di Neon (PgBouncer in transaction mode) non supporta i cursori lato server |
| `connect_timeout: 10` | se la porta 5432 è filtrata dalla rete, la connessione fallisce in 10 secondi invece di restare appesa |

---

## 8. Che cosa manca ancora, e chi lo porta

Alla fine dell'import, `GRA-A1-003` esiste su Neon con tutti i suoi metadati, ma:

- le sue **9 sezioni sono vuote**, con `formato_web = "todo"` e un segnaposto `TODO_FONTE`;
- non ha **nessun quiz**;
- il suo stato è `DA_SVILUPPARE_MVP`, quindi l'API risponde con `sezioni: []` e `quiz: []`
  e il sito mostra «lezione in preparazione».

**Il workbook dà lo scheletro, non la carne.** I testi definitivi arrivano da un secondo
canale, completamente separato: i brief markdown in `lezioni_markdown/`, pubblicati con

```bash
python manage.py pubblica_da_markdown \
  ../lezioni_markdown/A1/grammatica/003-gra-a1-003-il-verbo-to-be-forma-affermativa.md
```

Quel comando non passa da `importer.py`: ha un motore proprio,
[markdown_source.py](../backend/learning/markdown_source.py). Sostituisce le 9 sezioni
segnaposto con **6 sezioni reali**, crea i due quiz (4 quesiti guidati, 10 finali) e porta
la lezione in stato `PUBBLICATA`. A differenza dell'import, tocca **solo quella lezione**.

```
                    ┌─────────────────────┐
   workbook  ─────► │  learning_lezione   │ ◄───── (metadati: nome, ordine, durata…)
                    │  GRA-A1-003         │
                    └──────────┬──────────┘
                               │
              ┌────────────────┴─────────────────┐
              ▼                                  ▼
     struttura_lezione                    struttura_quiz
     9 sezioni TODO ✗                     nessuno ✗          ← dopo l'import del workbook
              │                                  │
              │  pubblica_da_markdown            │
              ▼                                  ▼
     6 sezioni reali ✓                    guidato (4) ✓
     testo/lista/errore_box               finale (10) ✓      ← dopo il brief markdown
```

⚠️ **Le due fasi non commutano.** Rieseguire `importa_contenuti` cancella di nuovo tutto e
riporta lo stato a `DA_SVILUPPARE_MVP`. Dopo ogni import **vanno ripubblicati i brief**.
È esattamente il lavoro che fa `importa_in_sicurezza`, che in più crea un branch di backup
su Neon prima di cominciare.

---

## Appendice — come riprodurre questa traccia

Tutti i valori di questo documento sono stati ottenuti eseguendo il codice. Ecco come
rifarlo.

### Vedere il dizionario `data`

```bash
cd backend
POSTGRES_DB= ../.venv/bin/python -c "
import os, django, json
os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; django.setup()
from learning.importer import load_source
d = load_source('../programma_lezioni_inglese_no_audio.xlsx')
for k, v in d.items(): print(f'{k:9} {type(v).__name__:5} len={len(v)}')
print(json.dumps(d['meta'], ensure_ascii=False, indent=2))
print(json.dumps(next(l for l in d['lezioni'] if l['id']=='GRA-A1-003'), ensure_ascii=False, indent=2))
"
```

### Vedere le 9 sezioni di una lezione

```bash
POSTGRES_DB= ../.venv/bin/python -c "
import os, django, json
os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; django.setup()
from learning.importer import load_source
d = load_source('../programma_lezioni_inglese_no_audio.xlsx')
for s in [x for x in d['sezioni'] if x['lezione_id']=='GRA-A1-003']:
    print(json.dumps(s, ensure_ascii=False, indent=2))
"
```

### Catturare il SQL, senza toccare Neon

Serve un modulo di settings separato, perché sovrascrivere `settings.DATABASES` dopo
`django.setup()` **non funziona**: il gestore delle connessioni di Django ha già la
configurazione in cache e continuerebbe a usare il database vero.

```bash
# 1. un settings usa e getta che punta a un SQLite temporaneo
cat > /tmp/settings_traccia.py <<'EOF'
from config.settings import *          # noqa
DEBUG = True
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "/tmp/traccia.sqlite3"}}
EOF

# 2. eseguire l'import registrando le query
cd backend
rm -f /tmp/traccia.sqlite3
PYTHONPATH=/tmp:. DJANGO_SETTINGS_MODULE=settings_traccia ../.venv/bin/python -c "
import django, io; django.setup()
from django.db import connection, connections
print('DB:', connections['default'].settings_dict['NAME'])   # deve dire /tmp/traccia.sqlite3
from django.core.management import call_command
call_command('migrate', verbosity=0, stdout=io.StringIO())
from django.test.utils import CaptureQueriesContext
from learning.importer import import_content
with CaptureQueriesContext(connection) as cap:
    print(import_content('../programma_lezioni_inglese_no_audio.xlsx'))
q = [' '.join(x['sql'].split()) for x in cap.captured_queries]
print(f'{len(q)} query')
for s in q:
    if 'GRA-A1-003' in s and s.startswith('INSERT'): print(s[:900]); break
"
```

Controlla sempre che la prima riga stampi `/tmp/traccia.sqlite3`: se stampa un altro
percorso, l'override non ha funzionato e staresti scrivendo sul database reale.

### Validare senza scrivere

```bash
cd backend
python manage.py valida_contenuti ../programma_lezioni_inglese_no_audio.xlsx
python manage.py valida_contenuti ../programma_lezioni_inglese_no_audio.xlsx --json
python manage.py importa_contenuti ../programma_lezioni_inglese_no_audio.xlsx --dry-run
python manage.py pubblica_da_markdown <file.md> --dry-run
```

---

## Documenti collegati

- [Funzionamento.md](Funzionamento.md) — com'è fatto il progetto, file per file
- [Fasi_di_Costruzione.md](Fasi_di_Costruzione.md) — storia delle decisioni e delle migration
- [Logica_Didattica.md](Logica_Didattica.md) — perché il programma è strutturato così
- [lezioni_markdown/_schema.md](../lezioni_markdown/_schema.md) — schema editoriale dei brief
- [README.md](../README.md) — comandi e avvio
