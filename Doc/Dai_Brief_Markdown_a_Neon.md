# Dal brief markdown a Neon — struttura e quiz della lezione

> **Cosa copre.** Il secondo binario dell'importazione: come un file di
> `lezioni_markdown/` diventa le sezioni e i quiz che l'utente vede nell'app.
> È il seguito di [Importazione_Excel_Neon.md](Importazione_Excel_Neon.md), che
> copre il primo binario: l'Excel porta il *catalogo*, il markdown porta il *contenuto*.
>
> **Lezione campione.** La stessa dell'altro documento:
> `GRA-A1-003 — Il verbo to be: forma affermativa`.
>
> **I valori riportati non sono di esempio: sono stati catturati eseguendo davvero
> `parse_markdown_lesson()`** sul brief reale.
>
> File di riferimento: [backend/learning/markdown_source.py](../backend/learning/markdown_source.py), 244 righe.

---

## Indice

1. [I due binari, e perché sono due](#1-i-due-binari-e-perché-sono-due)
2. [Il brief: che cosa viene letto e che cosa no](#2-il-brief-che-cosa-viene-letto-e-che-cosa-no)
3. [Le sezioni: quattro regole di forma](#3-le-sezioni-quattro-regole-di-forma)
4. [L'esercizio guidato](#4-lesercizio-guidato)
5. [Il quiz finale: domande e soluzioni appaiate](#5-il-quiz-finale-domande-e-soluzioni-appaiate)
6. [La scrittura su Neon](#6-la-scrittura-su-neon)
7. [Che cosa arriva al browser](#7-che-cosa-arriva-al-browser)
8. [I punti fragili, con prove](#8-i-punti-fragili-con-prove)
9. [Tre fonti di verità: la strategia](#9-tre-fonti-di-verità-la-strategia)

---

## 1. I due binari, e perché sono due

```
  programma_lezioni_inglese_no_audio.xlsx        lezioni_markdown/**/*.md
              │                                            │
              │  importa_contenuti                         │  pubblica_da_markdown
              │  (tutto il catalogo, in blocco)            │  (UNA lezione per volta)
              ▼                                            ▼
   learning_lezione ........... 98 righe          struttura_lezione ... le sezioni VERE
   struttura_lezione .......... 824 scheletri     struttura_quiz ...... guidato + finale
                                TODO_FONTE        learning_lezione .... stato → PUBBLICATA
              └──────────────────────┬─────────────────────┘
                                     ▼
                          Neon Postgres 17
                                     │  API REST
                                     ▼
                          frontend/src/components/Section.jsx
```

L'Excel sa **quali** lezioni esistono e in che ordine; non sa che cosa dicono.
Il brief markdown sa che cosa dice **una** lezione; non sa nulla del percorso.
Si incontrano per la prima volta dentro Postgres, sulla riga di `learning_lezione`
che entrambi indicano con lo stesso `id`: `GRA-A1-003`.

Oggi i brief pronti sono **48 su 98** (quelli con
`content_status: "testo-definitivo-verificato"` nel frontmatter).

## 2. Il brief: che cosa viene letto e che cosa no

Un brief è lungo ~168 righe e contiene molto materiale: scheda della lezione,
intento didattico, prerequisiti, contratto editoriale, checklist di verifica.
**Di tutto questo il parser legge due cose sole.**

### 2A. Il frontmatter — una riga sola conta

```yaml
---
id: "GRA-A1-003"          # ← l'UNICO campo che il parser usa
title: "Il verbo to be: forma affermativa"
area: "Grammatica"
level: "A1"
duration_minutes: 12
prerequisites: ["GRA-A1-002"]
content_status: "testo-definitivo-verificato"    # ← letto da importa_in_sicurezza, non dal parser
...
---
```

[`_parse_frontmatter`](../backend/learning/markdown_source.py#L34-L43) è un mini-parser
YAML da dieci righe: spezza su `:`, toglie le virgolette, restituisce un dizionario di
stringhe. Poi [riga 181](../backend/learning/markdown_source.py#L181) prende `id` e
**butta via tutto il resto**.

Non è una svista: `title`, `area`, `level`, `duration_minutes`, `prerequisites` sono
già nel database, messi lì dall'Excel. Il frontmatter li ripete per comodità di chi
legge il file. Sono **duplicati**, e come tutti i duplicati possono divergere: se cambi
la durata nel brief, il database non se ne accorge. Torna il discorso al § 9.

L'unico altro campo che conta davvero è `content_status`, letto però da un'altra parte:
[importa_in_sicurezza.py](../backend/learning/management/commands/importa_in_sicurezza.py)
lo usa per decidere quali brief ripubblicare dopo un import.

### 2B. Il blocco di contenuto — il resto del file non esiste

```python
# riga 186
m = re.search(r"^## +" + re.escape(CONTENT_HEADING) + r"\s*\n(.*?)(?=^## )", body, re.DOTALL | re.MULTILINE)
```

Viene isolato **solo** ciò che sta fra `## Contenuto definitivo da pubblicare` e il
successivo `## `. Nel nostro brief: le righe 59-140. Tutto quello che sta prima (scheda,
intento, prerequisiti) e dopo (contratto editoriale, checklist) è documentazione per
esseri umani e non raggiunge mai il database.

Nota la lookahead `(?=^## )`: se il blocco fosse **l'ultimo** del file, senza un `##`
dopo di sé, la regex non troverebbe niente e il comando morirebbe con
`Blocco 'Contenuto definitivo da pubblicare' non trovato`. La sezione
`## Contratto editoriale per Claude` che segue non è decorativa: è ciò che chiude il blocco.

### 2C. Dentro il blocco: i `###` si smistano in tre destini

[Righe 193-203](../backend/learning/markdown_source.py#L193-L203):

| Heading `###` | Destino |
| --- | --- |
| `Esercizio guidato` | → `struttura_quiz` modalità `guidato` |
| `Esercizio finale` | → domande del quiz `finale` |
| `Soluzioni e spiegazioni` | → risposte del quiz `finale` |
| **qualunque altro** | → una riga di `struttura_lezione` |

Il default è «diventa una sezione». Il titolo del `###`, qualunque esso sia, finisce
tale e quale nella colonna `tipo_sezione`. Non c'è nessun elenco di sezioni ammesse.

Per `GRA-A1-003` il risultato reale è:

```
id GRA-A1-003 | sezioni 6 | guidato 4 | finale 10

 - Obiettivo della lezione            -> testo
 - Regola e uso                       -> lista
 - Struttura                          -> lista
 - Esempi con traduzione              -> lista
 - Errori tipici per chi parla italiano -> errore_box
 - Riepilogo                          -> lista
```

## 3. Le sezioni: quattro regole di forma

Il formato non è dichiarato da nessuna parte: viene **dedotto dalla forma del testo**.
[`_section_from_block`](../backend/learning/markdown_source.py#L73-L103) prova quattro
regole, in quest'ordine, e si ferma alla prima che scatta.

### Regola 1 — ci sono ❌ e ✅ → `errore_box`

Nel brief:

```markdown
- ❌ **I have 25 years.** → ✅ **I am 25 years old.** — In inglese l'età si esprime con *to be*.
```

Nel database:

```python
{'errato': 'I have 25 years.',
 'corretto': 'I am 25 years old.',
 'perche': "In inglese l'età si esprime con to be."}
```

La regex che lo spacca è `❌ ... → ✅ ... — ...`, [riga 80](../backend/learning/markdown_source.py#L80).
I tre separatori sono obbligatori e sono tre caratteri precisi: la freccia `→`, e il
trattino **lungo** `—` (em dash), non il trattino della tastiera.

### Regola 2 — c'è una tabella → `lista`

Nel brief:

```markdown
| Funzione | Forma | Esempio |
| --- | --- | --- |
| I | I am / I'm | I'm Italian. |
```

Nel database:

```python
{'formato_web': 'lista',
 'contenuto': {'titolo': 'Struttura',
               'elementi': ["I — I am / I'm — I'm Italian.",
                            "he, she, it — is / 's — She's tired.",
                            "you, we, they — are / 're — We're ready."]}}
```

**La tabella non sopravvive.** Le celle di ogni riga vengono incollate con ` — ` e
l'intestazione viene scartata ([riga 93](../backend/learning/markdown_source.py#L93)).
Non è un bug del parser: è che dall'altra parte, in `Section.jsx`, un formato `tabella`
non esiste. Il modello Excel per quella sezione dice «Tabella o schema»; il web mostra
un elenco puntato.

### Regola 3 — c'è un elenco `- ` → `lista`

Il caso più comune. I `**grassetti**` e i `*corsivi*` vengono rimossi da
[`_strip_md`](../backend/learning/markdown_source.py#L26-L31): il database conserva
testo nudo, nessun markup.

### Regola 4 — nient'altro → `testo`

I paragrafi vengono uniti in **una stringa sola** separata da spazi
([riga 101](../backend/learning/markdown_source.py#L101)). Tre paragrafi distinti nel
brief diventano un unico blocco nel database: la suddivisione in capoversi si perde.

## 4. L'esercizio guidato

Nel brief:

```markdown
### Esercizio guidato

1. Completa: I ___ Italian. **Risposta: am.**
```

Nel database:

```python
{'ordine': 1, 'tipo': 'completamento',
 'testo': 'Completa: I ___ Italian.',
 'opzioni': [],
 'risposta_corretta': 'am',
 'spiegazione': 'Risposta corretta: «am».'}
```

Il marcatore `**Risposta: ...**` fa due lavori insieme: dà la soluzione e viene
**sottratto** dal testo della domanda ([riga 128](../backend/learning/markdown_source.py#L128)).
La spiegazione non è nel brief: è generata dal codice, sempre con la stessa frase.

Il guidato ammette solo il completamento — non esiste la scelta multipla.

## 5. Il quiz finale: domande e soluzioni appaiate

Qui il meccanismo è diverso: domande e risposte stanno in **due blocchi separati** del
file e vengono riappaiate per numero, non per posizione
([`_parse_final`](../backend/learning/markdown_source.py#L148-L174)).

```
### Esercizio finale              ### Soluzioni e spiegazioni
4. Scegli: ...                 ←→  4. **He is a doctor.** La professione...
```

Le chiavi sono i numeri scritti nel markdown. Se le due numerazioni non combaciano,
l'appaiamento sbaglia silenziosamente.

### Due dialetti dentro la domanda

**`Scegli:` all'inizio → scelta multipla.** Le opzioni si ricavano spezzando su `/`:

```markdown
4. Scegli: *He is doctor* / *He is a doctor*.
```

```python
{'tipo': 'scelta_multipla',
 'testo': 'Scegli la frase corretta.',
 'opzioni': ['He is doctor', 'He is a doctor.'],
 'risposta_corretta': 'He is a doctor.'}
```

Nota che il testo originale della domanda **viene buttato** e sostituito dalla frase
fissa `Scegli la frase corretta.` ([riga 164](../backend/learning/markdown_source.py#L164)).

**` / ` nella soluzione → risposte multiple accettate.** Diventano un'unica stringa con
il separatore `|`:

```markdown
7. **I am Italian. / I'm Italian.** Entrambe le forme sono corrette.
```

```python
{'tipo': 'completamento',
 'testo': 'Traduci: «Sono italiano.»',
 'risposta_corretta': "I am Italian.|I'm Italian.",
 'spiegazione': 'Entrambe le forme sono corrette.'}
```

Il `|` non è markdown né SQL: è una convenzione interna che qualcuno, al momento della
correzione, deve sapere di dover spezzare.

## 6. La scrittura su Neon

[`publish_markdown_lesson`](../backend/learning/markdown_source.py#L208-L244), tutto
dentro `@transaction.atomic`:

```python
StrutturaLezione.objects.filter(lezione=lesson).delete()      # solo questa lezione
StrutturaLezione.objects.bulk_create([...])                   # ordine 1..6, in ordine di file
StrutturaQuiz.objects.filter(lezione=lesson).delete()
# un StrutturaQuiz per modalità, con i suoi quesiti
lesson.stato_id = "PUBBLICATA"
lesson.save(update_fields=["stato"])
```

È lo stesso «cancella e ricostruisci» dell'import Excel, ma con `filter(lezione=...)` al
posto di `all()`: **chirurgico**. Le altre 97 lezioni non vengono sfiorate.

L'`ordine` delle sezioni è la posizione nel file, non il numero del modello Excel:
`enumerate(..., start=1)`. Riordinare i `###` nel markdown riordina la pagina web.

### Il numero delle sezioni cambia, e nessuno lo controlla

| | sezioni | quali |
| --- | --- | --- |
| Modello Excel per un'area GRA | **9** | incluse `Esercizio guidato` e `Esercizio finale` come *sezioni* |
| Dopo `pubblica_da_markdown` | **6** | gli esercizi sono diventati *quiz*, e manca `Confronto con forme simili` |

Anche i nomi divergono: l'Excel scrive `Regola e quando si usa`, il brief
`Regola e uso`; `Errori tipici degli italiani` contro `Errori tipici per chi parla
italiano`. La colonna `tipo_sezione` contiene quindi vocabolari diversi a seconda di
chi ha scritto per ultimo.

L'invariante «GRA deve avere 9 sezioni» (`AREA_SECTION_COUNTS` in
[importer.py:24](../backend/learning/importer.py#L24)) **non viene mai verificata su
questo binario**: `collect_source_structure_errors` gira su `data`, cioè sulla fonte
Excel, mentre `publish_markdown_lesson` non chiama nessuna validazione. È l'unica
scrittura del progetto che entra nel database senza passare da un controllo.

## 7. Che cosa arriva al browser

Il serializer espone quattro campi ([serializers.py:126-129](../backend/learning/serializers.py#L126-L129)):

```python
fields = ["ordine", "tipo_sezione", "contenuto", "formato_web"]
```

e `Section.jsx` fa uno `switch` su `formato_web`: `errore_box` → componenti `ErrorBox`,
`lista` → `<ul>`, tutto il resto → `<h2>` + `<p>`. **Tre formati soli.** Ogni ricchezza
del markdown che non entra in questi tre stampi si perde per strada.

Sui quesiti, `risposta_corretta` e `spiegazione` sono deliberatamente **fuori** dai
`fields` ([serializers.py:132-133](../backend/learning/serializers.py#L132-L133)): la
soluzione non lascia il server prima della correzione. Il `|` delle risposte multiple
resta quindi un affare interno all'API.

## 8. I punti fragili, con prove

**1. Una domanda senza risposta sparisce in silenzio.** In `_parse_guided`, un item
numerato privo di `**Risposta:**` incontra un `continue`
([riga 126](../backend/learning/markdown_source.py#L126)): niente errore, niente avviso,
la domanda semplicemente non esiste più. Nel quiz finale va anche peggio: una domanda
senza soluzione corrispondente riceve `risposta_corretta: ''` e viene salvata così.

**2. Le opzioni della scelta multipla si tradiscono da sole.** Guarda il caso reale del
§ 5: `['He is doctor', 'He is a doctor.']`. Il punto finale della riga markdown è
finito attaccato alla seconda opzione — che è quella giusta. Lo studente non ha bisogno
di sapere l'inglese: gli basta scegliere l'opzione con il punto.

**3. Nessuna validazione.** Il vincolo «il quiz finale deve avere 8-10 quesiti» esiste
([importer.py](../backend/learning/importer.py#L400-L401)) ma vive sul binario Excel,
che i quiz non li ha mai. Su questo binario, che i quiz li produce davvero, non viene
applicato.

**4. `importa_contenuti` cancella tutto.** `StrutturaLezione.objects.all().delete()`
spazza via anche le sezioni pubblicate dai brief e riporta gli stati a quelli del
workbook. È il motivo per cui esiste `importa_in_sicurezza`, che ripubblica in coda.
La rete c'è, ma è una toppa su un ordine di operazioni sbagliato.

**5. Serve il terminale.** Pubblicare richiede il portatile, il `.env` con le
credenziali Neon e un comando `manage.py`. Non si corregge un refuso dal telefono.

## 9. Tre fonti di verità: la strategia

Hai detto che avresti preferito il corpo della lezione interamente sul web. Prima di
scegliere, conviene vedere il problema per quello che è.

Oggi il progetto ha **tre** depositi che si sovrappongono:

| | contiene | chi lo modifica |
| --- | --- | --- |
| Excel | catalogo, ordine, metadati | tu, a mano |
| Markdown | testo, esercizi, quiz + **una copia dei metadati** nel frontmatter | tu (con l'AI) |
| Postgres | tutto, fuso insieme | i due comandi |

Il fastidio che senti non nasce dal markdown: nasce dal fatto che **il contenuto vive in
un posto e si vede in un altro**, e per passare dall'uno all'altro serve un comando da
terminale, che per giunta può perdere pezzi senza dirtelo. Sono due problemi distinti,
e il secondo si risolve senza toccare il primo.

### Le tre strade

**A. Restare così, ma chiudere il ciclo.** Markdown fonte, con tre aggiunte: parser
severo (se una domanda non ha risposta, il comando si ferma invece di scartarla);
pubblicazione automatica su push (GitHub Action che lancia `pubblica_da_markdown` sui
file cambiati); anteprima locale. È il modello *docs-as-code*: quello che usa la
documentazione di Stripe o di React.
*Costo:* piccolo, incrementale. *Ottieni:* la fine delle perdite silenziose e del
terminale obbligatorio. *Non ottieni:* scrivere dal browser.

**B. Il database come fonte, editor sul web.** Django admin (o una pagina tua) per
modificare sezioni e quesiti, il markdown declassato a export di backup.
*Costo:* medio-alto — serve un editor per tre formati diversi, i ruoli, la validazione,
e soprattutto **perdi git**: niente diff, niente cronologia, niente «com'era questa
lezione un mese fa» se non con i branch Neon.
*Ottieni:* correggi un refuso dal telefono in dieci secondi.

**C. Ibrido con una regola di precedenza.** Markdown per scrivere, web per correggere,
e una regola scritta su chi vince quando divergono. È la strada più attraente e la più
pericolosa: senza una direzione unica, prima o poi `pubblica_da_markdown` cancellerà una
correzione fatta dal web, esattamente come oggi `importa_contenuti` cancella i brief.

### Cosa farei io

**A adesso, B più avanti — e mai C senza una regola scritta.**

Il motivo è aritmetico: hai 48 brief già scritti e verificati, ed è lì che sta il valore.
Il markdown ti dà tre cose che un CMS non ti dà: la cronologia in git, la possibilità di
far scrivere una lezione all'AI dandole in pasto un file, e un formato che sopravvive al
progetto. Il vero difetto non è dove stanno i testi: è che **il tuo Excel e il tuo
frontmatter dicono le stesse cose in due posti**, e che la pubblicazione è muta quando
perde qualcosa.

Se un giorno la scrittura dal web ti servirà davvero, il passaggio giusto sarà quello
di cui parlavamo per le sezioni: separare lo scheletro calcolato dal contenuto scritto,
e a quel punto un editor web tocca solo la seconda tabella senza rischiare di cancellare
niente.

L'ordine dei lavori, in scala di valore per ora spesa:

1. **Parser severo** — mezza giornata, elimina la classe di bug peggiore (perdite mute).
2. **Un solo posto per i metadati** — o li toglie il frontmatter, o li ignora l'Excel.
3. **Pubblicazione senza terminale** — GitHub Action, oppure un pulsante nell'admin.
4. **Solo dopo**, se ancora serve: l'editor web.
