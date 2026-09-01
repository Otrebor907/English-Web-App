# Prima conversazione — MVP

SPA testuale per adulti italiani che imparano l'inglese: catalogo per area e livello, contenuti a scorrimento, esercizio guidato e quiz finale con punteggio. Il backend è Django + Django REST Framework; il frontend è React + Vite. Il database è PostgreSQL (Neon) quando le variabili `POSTGRES_*` sono impostate, SQLite altrimenti.

Nessuna lezione è mai bloccata: l'ordine consigliato è espresso da `ordine_mvp` e `ordine_percorso`, ma la navigazione è libera e i progressi sono informativi.

## Avvio locale

Requisiti: Python 3.13 e Node.js 22 con pnpm (le versioni usate dalla CI).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python manage.py migrate
python manage.py importa_contenuti fixtures/contenuti_minimi.json
python manage.py runserver
```

In un secondo terminale:

```bash
cd frontend
pnpm install
pnpm dev
```

Aprire `http://localhost:5173`, registrarsi con nome, cognome, email e password (almeno 8 caratteri) e iniziare. Le API sono esposte su `http://localhost:8000/api/`.

`fixtures/contenuti_minimi.json` carica 3 lezioni finte, sufficienti a far girare l'app. Per il catalogo reale vedi [Import contenuti](#import-contenuti).

Su macOS lo script `avvia-sito.command` fa tutto con un doppio clic: migrazioni, backend, frontend e apertura del browser.

## Verifiche

```bash
cd backend
../.venv/bin/python manage.py test -v 2

cd ../frontend
pnpm build
```

61 test coprono: import idempotente e atomico, validazione della fonte, rifiuto dei frammenti JSON non importabili, assenza di campi audio, accesso anonimo in lettura e blocco in scrittura, assegnazione al percorso personale, esercizio guidato non conteggiato nel punteggio, quiz finale con scoring server-side, policy delle password, aggiornamento profilo, header anti-clickjacking e guardiano della configurazione.

Il test end-to-end (`FullUserJourneyTests`) percorre registrazione, catalogo, apertura della lezione, quiz con punteggio calcolato dal server e completamento.

Per eseguire i test senza toccare il database Neon, forzare SQLite:

```bash
POSTGRES_DB= ../.venv/bin/python manage.py test
```

## Import contenuti

I contenuti arrivano da **due fonti distinte**, in due passaggi.

### 1. Il workbook: catalogo e scheletro

```bash
python manage.py valida_contenuti ../programma_lezioni_inglese_no_audio.xlsx
python manage.py valida_contenuti ../programma_lezioni_inglese_no_audio.xlsx --json
python manage.py importa_contenuti ../programma_lezioni_inglese_no_audio.xlsx --dry-run
python manage.py importa_contenuti ../programma_lezioni_inglese_no_audio.xlsx
```

`importa_contenuti` è idempotente e atomico: valida tutto prima di scrivere e, in caso di errore, termina con `IMPORT FALLITO` senza salvare modifiche. `--dry-run` esegue le validazioni senza scrivere. `valida_contenuti` produce un riepilogo con conteggi, errori e avvisi; `--json` è pensato per la CI.

`load_source` accetta due sole fonti: il workbook del programma (`.xlsx`/`.xlsm` con i sei fogli `Programma Lezioni`, `Percorso MVP`, `Grammatica`, `Vocabolario`, `Comunicazione`, `Liste`) e il JSON ([backend/fixtures/contenuti_minimi.json](backend/fixtures/contenuti_minimi.json) è quello di riferimento). Un `.xlsx` privo di quei fogli viene rifiutato con l'elenco di quelli mancanti.

Dal workbook vengono estratti:

- le lookup e i codici area (`Grammatica` → `GRA`) dal foglio `Liste`;
- le 98 lezioni con i loro metadati, categoria compresa;
- le assegnazioni del `Percorso MVP`, con il solo `Ordine MVP`;
- i template delle sezioni: 9 per Grammatica, 7 per Vocabolario, 8 per Comunicazione.

Le colonne `Prerequisiti`, `Lezione Precedente` e `Lezione Successiva` esistono ancora nel foglio ma **non vengono lette**: il grafo dei prerequisiti è stato rimosso con la migration `0008`.

Il workbook è un programma editoriale: non contiene i testi definitivi né i quesiti. Le sezioni che ne derivano sono marcate `TODO_FONTE`, non viene creato alcun quiz, e l'import non trasforma `Da sviluppare (MVP)` in `Pubblicata`.

Il foglio `Percorso MVP` contiene materialmente 28 righe. In applicazione dell'aggiornamento di perimetro, il parser inserisce `GRA-A1-008` all'ordine MVP 11 e incrementa di uno gli ordini successivi, arrivando a 29. Il report segnala sempre questa normalizzazione; quando il workbook con 29 righe sarà disponibile non verrà applicata.

### 2. I brief markdown: i testi definitivi

```bash
python manage.py pubblica_da_markdown ../lezioni_markdown/A1/grammatica/003-gra-a1-003-il-verbo-to-be-forma-affermativa.md
python manage.py pubblica_da_markdown <file.md> --dry-run
```

Ogni lezione ha un brief in [lezioni_markdown/](lezioni_markdown/) (`<livello>/<area>/<ordine>-<id>-<slug>.md`). Il parser legge **solo** il blocco `## Contenuto definitivo da pubblicare` e ne ricava sezioni, esercizio guidato e quiz finale; il formato di ciascuna sezione è dedotto dalla forma del testo (`❌`/`✅` → box errore, tabella o elenco → lista, altrimenti testo).

A differenza dell'import del workbook, la pubblicazione è **chirurgica**: sostituisce sezioni e quiz della sola lezione indicata e la porta in stato `PUBBLICATA`, senza toccare le altre.

⚠️ Rieseguire `importa_contenuti` cancella **tutte** le sezioni e i quiz e riporta gli stati a quelli del workbook: dopo ogni import vanno ripubblicati i brief.

### 3. I due passaggi in uno, con rete di sicurezza

```bash
python manage.py importa_in_sicurezza --dry-run     # mostra il piano
python manage.py importa_in_sicurezza               # esegue
```

Fa tre cose in fila: crea un **branch di backup su Neon**, importa il workbook, ripubblica tutti i brief marcati `content_status: "testo-definitivo-verificato"`. È il modo corretto di lanciare un import, perché ripara da solo ciò che l'import cancella.

Il branch serve perché il piano Free di Neon conserva la cronologia **solo 6 ore**: un import sbagliato scoperto il giorno dopo non è più recuperabile con l'instant restore, mentre un branch resta finché non lo cancelli.

| Opzione | Effetto |
| --- | --- |
| `--dry-run` | elenca i brief che pubblicherebbe; non tocca né Neon né il database |
| `--tieni N` | quanti branch di backup conservare (default 5). I più vecchi vengono cancellati |
| `--senza-backup` | salta il branch; usalo solo se non hai le credenziali Neon |
| `--brief PATH` | cartella dei brief (default `lezioni_markdown/`) |

Richiede `NEON_API_KEY` e `NEON_PROJECT_ID` in `.env` (vedi [.env.example](.env.example)). Senza credenziali il comando **si ferma prima di importare**: la rete di sicurezza non è opzionale per sbaglio.

I branch di backup si chiamano `backup-AAAAMMGG-HHMM`. La potatura cancella **solo** i nomi che rispettano esattamente quello schema, quindi un branch creato a mano non viene mai toccato. Attenzione al tetto del piano Free: **10 branch per progetto**, non aumentabili.

Il client della Management API di Neon è [backend/learning/neon.py](backend/learning/neon.py): usa `urllib` della standard library, nessuna dipendenza nuova. Amministra solo i branch — i dati continuano a passare dall'ORM su connessione Postgres diretta.

### Validazioni imposte sulla fonte

Le lookup alimentate dalla fonte sono `area`, `tipologia`, `livello`, `difficolta`, `stato`. Le sole aree accettate sono GRA, VOC e COM. Il validatore impone 9/7/8 sezioni per area, 98 lezioni con `ordine_percorso` una permutazione continua di 1–98, 29 posizioni MVP continue e 8–10 quesiti per ogni quiz finale. Qualunque campo il cui nome contiene `audio` viene respinto, a qualsiasi profondità.

## Regole applicate

- Nessuna lezione è bloccata: `ordine_mvp` e `ordine_percorso` sono un consiglio, non un cancello.
- `/api/percorso/` ordina per `ordine_mvp`; `/api/lezioni/indice/` ordina per area e `ordine_percorso`, e raggruppa per `categoria`.
- Il contenuto teorico è pubblico; esercizi, progressi e assegnazione al percorso richiedono l'accesso.
- Le lezioni non `PUBBLICATA` sono comunque visibili, ma l'API restituisce metadati con `sezioni` e `quiz` vuoti e il frontend mostra «in preparazione».
- Le risposte corrette e le spiegazioni restano sul server: non compaiono nel payload dei quesiti prima della verifica.
- Il quiz finale è superato al 70%, è ripetibile e conserva il punteggio migliore; superarlo assegna la lezione al percorso personale.
- L'esercizio guidato non produce punteggio.
- Nei quesiti di completamento il confronto ignora maiuscole e spazi; più risposte accettate si separano con `|`.
- Non sono presenti audio, registrazione vocale, AI, spaced repetition o drag & drop.

## Produzione

Impostare le variabili `POSTGRES_*` mostrate in [.env.example](.env.example), una `DJANGO_SECRET_KEY` sicura, `DJANGO_DEBUG=0`, host e origini consentiti. Il deploy e la gestione dei segreti non fanno parte di questo scheletro MVP.

## Docker e PostgreSQL

Con Docker installato:

```bash
docker compose up --build
```

La SPA sarà disponibile su `http://localhost:8080`, Django su `http://localhost:8000` e PostgreSQL (`postgres:17-alpine`) resterà nel volume `postgres_data`. Il workbook viene montato in sola lettura nel backend come `/data/programma_lezioni_inglese_no_audio.xlsx`.

Per inizializzare il database Docker con la fixture tecnica:

```bash
docker compose exec backend python manage.py importa_contenuti fixtures/contenuti_minimi.json
```

## Amministrazione editoriale

Il pannello Django Admin non esiste più, e con lui il comando `createsuperuser` (arrivava da `django.contrib.auth`, ora non installata). Per creare un amministratore:

```bash
python manage.py shell -c "from learning.models import User; User.objects.create_superuser(email='tu@example.com', password='...')"
```

I contenuti si pubblicano con `importa_contenuti` e `pubblica_da_markdown`; i dati si ispezionano su Neon. Un utente staff autenticato nella SPA vede `/contenuti-da-completare`, con il riepilogo delle sezioni `TODO_FONTE` e dei quiz finali mancanti.

## Documentazione

- [Doc/Funzionamento.md](Doc/Funzionamento.md) — come è fatto il progetto, file per file.
- [Doc/Fasi_di_Costruzione.md](Doc/Fasi_di_Costruzione.md) — storia delle decisioni e delle migration.
- [Doc/Logica_Didattica.md](Doc/Logica_Didattica.md) — perché il programma è strutturato così, e la roadmap di prodotto.
- [lezioni_markdown/_schema.md](lezioni_markdown/_schema.md) — schema editoriale dei brief.

## CI

La workflow [.github/workflows/ci.yml](.github/workflows/ci.yml) esegue `manage.py check`, il controllo che non esistano migrazioni non generate (`makemigrations --check`), i test backend, la build React e la validazione JSON del workbook (98 lezioni, MVP 29). Tutti gli step devono essere verdi.
