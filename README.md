# Prima conversazione — MVP

SPA testuale per adulti italiani che imparano l'inglese, con percorso a prerequisiti, contenuti per area, esercizi guidati e quiz finali. Il backend è Django + Django REST Framework; il frontend è React + Vite. SQLite è il database locale, PostgreSQL quello previsto in produzione.

## Avvio locale

Requisiti: Python 3.11+ e Node.js 20+ con npm/pnpm.

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

Aprire `http://localhost:5173`, registrarsi con email e password (minimo 8 caratteri) e iniziare il percorso. Le API sono esposte su `http://localhost:8000/api/`.

## Verifiche

```bash
cd backend
../.venv/bin/python manage.py test -v 2

cd ../frontend
pnpm build
```

Il test `PersistedPublishedGraphBuildTest` importa la fonte di esempio e fallisce se una lezione pubblicata non è raggiungibile dal primo `ordine_mvp`. Gli altri test coprono riferimenti inesistenti/fuori perimetro, ordine dei prerequisiti, cicli, attraversamento di lezioni non pubblicate, import idempotente, sblocco e scoring.

Il test end-to-end backend percorre realmente registrazione, accesso al percorso, apertura della lezione, quiz con scoring server-side, completamento e sblocco della lezione successiva.

## Import contenuti

Il comando è idempotente e atomico: valida tutto prima di scrivere e, in caso di errore, termina con `IMPORT FALLITO` senza salvare modifiche.

```bash
python manage.py importa_contenuti percorso/al/file.json
python manage.py importa_contenuti percorso/al/file.xlsx
python manage.py importa_contenuti percorso/al/file.xlsx --dry-run
python manage.py valida_contenuti percorso/al/file.xlsx
python manage.py valida_contenuti percorso/al/file.xlsx --json
```

`--dry-run` esegue tutte le validazioni senza scrivere. `valida_contenuti` produce un riepilogo completo con conteggi, errori e avvisi; `--json` è pensato per la CI.

Il JSON di riferimento è [backend/fixtures/contenuti_minimi.json](backend/fixtures/contenuti_minimi.json). L'importatore riconosce direttamente anche il workbook reale `programma_lezioni_inglese_no_audio.xlsx`, con i fogli `Programma Lezioni`, `Percorso MVP`, `Grammatica`, `Vocabolario`, `Comunicazione` e `Liste`.

Dal workbook reale vengono estratti:

- le lookup e i codici area del foglio `Liste`;
- tutte le 98 lezioni e i loro prerequisiti;
- le 29 assegnazioni del `Percorso MVP`, con ordine, importanza e priorità P0–P2;
- i template delle sezioni: 9 GRA, 7 VOC e 8 COM.

Il workbook è un programma editoriale, non contiene ancora i testi completi né i quesiti. Le sezioni generate dal parser sono quindi marcate `TODO_FONTE` e non viene creato alcun quiz. L'import non trasforma automaticamente `Da sviluppare (MVP)` in `Pubblicata`.

Il workbook locale precedente contiene materialmente 28 righe nel foglio `Percorso MVP`. In applicazione dell'aggiornamento di perimetro, il parser inserisce esplicitamente `GRA-A1-008` all'ordine MVP 11 con importanza `Consigliata` e priorità `P1`, quindi incrementa di uno gli ordini successivi. Il report segnala sempre questa normalizzazione; quando il workbook/JSON ufficiale con 29 righe sarà disponibile non verrà applicata.

Per il formato Excel normalizzato alternativo sono richiesti questi fogli:

- `Liste`: `categoria`, `code`, `nome`;
- `Lezioni`: i campi del modello, inclusi `priorita` e `importanza_mvp`; `competenze` ed `errori_tipici` sono array JSON;
- `Prerequisiti`: `lezione_id`, `richiede_lezione_id`;
- `Sezioni`: `lezione_id`, `ordine`, `tipo_sezione`, `contenuto` (oggetto JSON), `formato_web`;
- `Quiz`: una riga per quesito con `lezione_id`, `modalita`, `ordine`, `tipo`, `testo`, `opzioni` (array JSON), `risposta_corretta`, `spiegazione`.

Le categorie ammesse in `Liste.categoria` sono `area`, `tipologia`, `livello`, `difficolta`, `stato`, `importanza`. Le sole aree accettate sono GRA, VOC e COM. Il validatore impone rispettivamente 9/7/8 sezioni, 98 lezioni con `ordine_percorso` continuo 1–98, 29 posizioni MVP continue e 8–10 quesiti per ogni quiz finale. Qualunque campo il cui nome contiene `audio` viene respinto.

## Regole applicate

- La navigazione usa esclusivamente `ordine_mvp`.
- `priorita` ordina il lavoro editoriale: P0 Essenziale, P1 Consigliata, P2 Secondaria, P3 post-MVP. Non sostituisce `ordine_mvp` nella navigazione utente.
- Una lezione è disponibile soltanto quando tutti i prerequisiti sono completati.
- Il DAG rifiuta cicli, riferimenti inesistenti, prerequisiti con ordine uguale/superiore e lezioni pubblicate non raggiungibili.
- Le risposte corrette restano sul server; il punteggio finale è calcolato dall'API.
- Il quiz è superato al 70%, è ripetibile e conserva il punteggio migliore.
- Non sono presenti audio, registrazione vocale, AI, spaced repetition o drag & drop.

## Produzione

Impostare le variabili `POSTGRES_*` mostrate in [.env.example](.env.example), una chiave `DJANGO_SECRET_KEY` sicura, `DJANGO_DEBUG=0`, host e origini consentiti. Il deploy e la gestione dei segreti non fanno parte di questo scheletro MVP.

## Docker e PostgreSQL

Con Docker installato:

```bash
docker compose up --build
```

La SPA sarà disponibile su `http://localhost:8080`, Django su `http://localhost:8000` e PostgreSQL resterà nella volume `postgres_data`. Il workbook viene montato in sola lettura nel backend come `/data/programma_lezioni_inglese_no_audio.xlsx`.

Per inizializzare il database Docker con la fixture tecnica:

```bash
docker compose exec backend python manage.py importa_contenuti fixtures/contenuti_minimi.json
```

L'import del workbook reale passa la validazione DAG dopo la normalizzazione dichiarata a 29 lezioni MVP. Le lezioni restano non pubblicate e con contenuti `TODO_FONTE` finché non arriva la fonte editoriale definitiva.

## Amministrazione editoriale

Creare un amministratore con:

```bash
python manage.py createsuperuser
```

Il Django Admin è su `/admin/`. Un utente staff autenticato nella SPA vede anche `/contenuti-da-completare`, con il riepilogo delle sezioni `TODO_FONTE` e dei quiz finali mancanti.

## CI

La workflow `.github/workflows/ci.yml` esegue controlli Django, migrazioni, test backend, build React e validazione JSON del workbook. Tutti gli step devono essere verdi, inclusa la validazione DAG del catalogo da 98 lezioni e dell'MVP da 29.
