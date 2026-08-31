# Funzionamento del progetto "Prima Conversazione"

> Guida pensata per chi conosce le basi di Python ma non ha ancora familiarità con un progetto web completo. Spiega **perché** abbiamo scelto questi strumenti, **cosa fa ogni file** e **come i pezzi comunicano tra loro**.

---

## 1. Cos'è questa app, in due frasi

È un sito (SPA = *Single Page Application*, "applicazione a pagina singola") per imparare l'inglese: l'utente si registra, sceglie una lezione di Grammatica/Vocabolario/Comunicazione, la legge, fa un esercizio guidato e un quiz finale con punteggio. Tutto scorre su **una singola pagina HTML** che cambia contenuto senza ricaricarsi (questo è il senso di "SPA").

Il progetto è diviso in due metà che si parlano via rete (API):

```
┌─────────────────────┐        richieste HTTP        ┌──────────────────────┐
│   FRONTEND (React)  │  ───────────────────────────► │   BACKEND (Django)   │
│  gira nel browser   │  ◄─────────────────────────── │  gira su un server   │
└─────────────────────┘        risposte JSON          └──────────┬───────────┘
                                                                   │
                                                                   ▼
                                                          ┌──────────────────┐
                                                          │  DATABASE         │
                                                          │  SQLite / Postgres│
                                                          └──────────────────┘
```

- Il **frontend** è quello che vedi e clicchi nel browser (bottoni, pagine, form).
- Il **backend** è il "cervello" che gestisce utenti, lezioni, punteggi: non lo vedi, risponde solo a richieste.
- Il **database** è dove tutto viene salvato in modo permanente (utenti, lezioni, progressi).

Non serve conoscere React o Django a fondo per seguire questa guida: ogni concetto tecnico viene spiegato la prima volta che compare.

---

## 2. Perché questo stack (le scelte tecnologiche)

| Livello | Scelta | Perché |
|---|---|---|
| Backend | **Python + Django** | Python è il linguaggio che già conosci. Django è un framework "batterie incluse": gestisce da solo utenti, autenticazione e database — non devi scrivere quella parte da zero. (Di quelle batterie il progetto ha poi rimosso il pannello admin: vedi Fase 7 in `Fasi_di_Costruzione.md`.) |
| API | **Django REST Framework (DRF)** | Django di base genera pagine HTML; DRF lo trasforma in un fornitore di dati puri (JSON) che il frontend può consumare. È lo standard de facto per fare API con Django. |
| Frontend | **React + Vite** | React è la libreria più diffusa per costruire interfacce che si aggiornano da sole quando i dati cambiano (niente di dover riscrivere manualmente l'HTML). Vite è lo strumento che impacchetta e serve il codice React in sviluppo/produzione: è molto più veloce dei tool più vecchi (es. Webpack). |
| Database (sviluppo) | **SQLite** | È un singolo file (`db.sqlite3`), zero configurazione: perfetto per lavorare in locale sul proprio computer. |
| Database (produzione) | **PostgreSQL** | Più robusto e scalabile per un sito online reale con più utenti contemporanei. Il codice sceglie automaticamente Postgres se trova le variabili `POSTGRES_*`, altrimenti usa SQLite (vedi `backend/config/settings.py`). |
| Contenitori | **Docker + docker-compose** | Permette di avviare backend, frontend e database tutti insieme con un solo comando, in un ambiente identico su qualunque macchina (niente "sul mio PC funzionava"). |
| Automazione test | **GitHub Actions (CI)** | Ogni volta che il codice viene inviato su GitHub, uno script automatico verifica che tutto funzioni ancora (test, build, validazione contenuti) prima che si possa considerare "sicuro". |

In sintesi: **Django/DRF = motore + magazzino dati**, **React/Vite = vetrina interattiva**, **SQLite→Postgres = dove si salvano i dati**, **Docker = scatola per spedire tutto insieme**.

---

## 3. Mappa delle cartelle

```
English-Web-App/
├── backend/                    ← Django: API, database, logica, autenticazione
│   ├── config/                 ← configurazione generale del progetto Django
│   ├── learning/                ← l'unica "app" Django: modelli, viste, regole
│   │   ├── migrations/          ← storico delle modifiche al database
│   │   ├── management/commands/ ← comandi custom (import/valida contenuti)
│   │   └── tests/                ← test automatici
│   ├── fixtures/                ← dati JSON di esempio per collaudo
│   ├── sources/                 ← sorgenti editoriali (JSON per singola lezione)
│   └── manage.py                ← telecomando per pilotare Django da terminale
├── frontend/                    ← React: interfaccia utente
│   └── src/                      ← codice sorgente React
├── lezioni_markdown/             ← testi delle lezioni scritti in Markdown (editoriale)
├── docker-compose.yml            ← ricetta per avviare tutto insieme con Docker
├── programma_lezioni_inglese_no_audio.xlsx  ← foglio Excel "regia" del programma didattico
└── .github/workflows/ci.yml      ← test automatici ad ogni push
```

---

## 4. Backend (Django) — file per file

### 4.1 `backend/manage.py`
Il "telecomando" di Django. Da terminale lo usi per: avviare il server (`runserver`), applicare modifiche al database (`migrate`), creare un amministratore (`createsuperuser`), lanciare i comandi custom di importazione contenuti, ecc. Non lo modifichi quasi mai: lo *usi* e basta.

### 4.2 `backend/config/` — la configurazione del progetto
Django distingue tra "progetto" (config generale) e "app" (un modulo funzionale, qui `learning`). `config/` contiene:

- **`settings.py`** — il pannello di controllo di tutto il backend:
  - `INSTALLED_APPS`: quali moduli sono attivi (DRF, `corsheaders`, la nostra app `learning`...). Volutamente corta: `django.contrib.admin`, `auth`, `contenttypes`, `sessions` e `messages` sono state disinstallate insieme al pannello `/admin/`.
  - `DATABASES`: sceglie **Postgres** se trova la variabile d'ambiente `POSTGRES_DB`, altrimenti **SQLite** — questo è il meccanismo che rende il progetto "portabile" tra locale e produzione.
  - `AUTH_USER_MODEL = "learning.User"`: dice a Django di usare il nostro utente custom (basato su email) invece di quello di default (basato su username).
  - `REST_FRAMEWORK`: impone che ogni richiesta all'API debba avere un **token** di autenticazione valido, salvo eccezioni esplicite (login, registrazione, contenuti pubblici).
  - `CORS_ALLOWED_ORIGINS`: elenco degli indirizzi (es. `localhost:5173`, dove gira il frontend) a cui è permesso chiamare l'API da un browser. Senza questo, il browser bloccherebbe le richieste per motivi di sicurezza (politica "same-origin").
- **`urls.py`** — lo "smistatore" principale: manda tutto ciò che inizia con `/api/` al file `learning/urls.py`. Non c'è altro: il pannello `/admin/` è stato rimosso.
- **`wsgi.py`** — il punto d'ingresso che i server di produzione (es. gunicorn, visto in `docker-compose.yml`) usano per far partire l'applicazione. Non lo tocchi mai a mano.

### 4.3 `backend/learning/` — l'app che contiene tutta la logica didattica

Questa è l'unica "app" Django del progetto: contiene modelli (le tabelle del database), viste (gli endpoint API) e la logica di business (regole del percorso, punteggio, ecc.).

- **`models.py`** — definisce le **tabelle del database** come classi Python (questo si chiama *ORM*: Object-Relational Mapping, cioè "scrivi classi Python, Django le traduce in tabelle SQL"). Le principali:
  - `User` (tabella `user_profile`): l'utente, con email al posto dello username.
  - `Lezione`: una lezione (grammatica/vocabolario/comunicazione), con area, livello e due ordinamenti: `ordine_percorso` (posizione nel programma completo, 1..98, sempre valorizzato) e `ordine_mvp` (posizione nel percorso MVP, 1..29, `NULL` per le lezioni fuori MVP).
  - `Prerequisito`: collega due lezioni dicendo "per fare X è consigliato aver fatto Y" (relazione "molti-a-molti" tramite tabella intermedia).
  - `StrutturaLezione` (tabella `struttura_lezione`): un blocco di contenuto teorico dentro una lezione (es. "Regola", "Esempio", "Errore tipico").
  - `StrutturaQuiz` (tabella `struttura_quiz`): il quiz della lezione, in modalità guidata o finale.
  - `QuesitoGuidato` e `QuesitoFinale` (tabelle `struttura_quiz_guidato` e `struttura_quiz_finale`): le singole domande, separate per modalità. Hanno colonne identiche, garantite da una classe base astratta condivisa. Attenzione: gli `id` sono univoci solo dentro la propria tabella, per questo la rotta di verifica include la modalità.
  - `Token` (tabella `user_authtoken_token`): il token di sessione dell'API, uno per utente. Eredita dal modello di DRF cambiando solo il nome della tabella.
  - `Progresso` (tabella `user_progress`): tiene traccia, per ogni coppia utente+lezione, dello stato (bloccata/disponibile/in corso/completata) e del punteggio migliore ottenuto.
  - Le classi `Area`, `Tipologia`, `Livello`, `Difficolta` e `StatoLezione` sono tabelle dimensione "codice → etichetta", su Neon chiamate `dim_area_lezione`, `dim_tipologia`, `dim_livello`, `dim_difficolta_lezione`, `dim_stato_lezione`. Servono a validare che i valori inseriti siano tra quelli ammessi. Il prefisso `dim_` è minuscolo perché Postgres abbassa gli identificatori non virgolettati: `SELECT * FROM dim_livello` funziona così com'è.
- **`serializers.py`** — i **traduttori** tra oggetti Python/database e JSON (il formato che il frontend capisce). Ogni serializer dice "quali campi esporre e come validarli in ingresso". Es. `RegisterSerializer` valida che la password abbia almeno 8 caratteri prima di creare l'utente.
- **`views.py`** — le **funzioni che rispondono alle richieste HTTP** (gli endpoint). Ogni funzione decorata con `@api_view([...])` è un endpoint: riceve una richiesta, fa i controlli, interroga il database tramite i modelli, e restituisce una `Response` in JSON. Esempi: `register` (crea utente + genera token), `path_lessons` (elenco delle lezioni del percorso MVP), `submit_final_quiz` (calcola il punteggio del quiz **lato server**, mai fidandosi di un punteggio calcolato dal browser).
- **`urls.py`** — collega ogni indirizzo (es. `POST /api/auth/login/`) alla funzione corrispondente in `views.py`.
- **`services.py`** — le **regole di business pure**, separate dalle viste per essere riutilizzabili e testabili. In particolare:
  - `authenticate_by_email`: verifica email + password contro l'hash salvato. Rimpiazza `django.contrib.auth.authenticate()`, e ne conserva la difesa contro il timing attack (calcola un hash anche quando l'email non esiste, così i tempi di risposta non rivelano quali email sono registrate).
  - `record_final_score`: salva il punteggio migliore, e se ≥ 70% marca la lezione come completata.
- **`auth.py`** — due sostituti di pezzi che Django/DRF fornirebbero: `AnonymousUser`, l'oggetto che DRF mette in `request.user` quando la richiesta non porta un token (quello di `django.contrib.auth` non è più disponibile), e `TokenAuthentication`, che cerca il token nel nostro modello invece che nella tabella `authtoken_token` di DRF.
- **`apps.py`** — file di configurazione minimo richiesto da Django per registrare l'app `learning`. Quasi mai lo tocchi.
- **`importer.py`** — il cuore dell'importazione contenuti: legge un file JSON o un foglio Excel (`.xlsx`), lo valida pesantemente (campi obbligatori, aree ammesse, conteggio sezioni per lezione, niente campi "audio"...) e infine scrive tutto nel database **in una singola transazione atomica** (`@transaction.atomic`): o va tutto a buon fine, o non si salva nulla — non esistono stati intermedi corrotti.
- **`markdown_source.py`** — un parser che legge i brief editoriali scritti a mano in `lezioni_markdown/*.md` (teoria + esercizio guidato + quiz finale con soluzioni) e pubblica **una singola lezione alla volta**, senza toccare le altre. Usa espressioni regolari per riconoscere pattern come `❌ sbagliato → ✅ corretto — perché` o `**Risposta: X**`.

### 4.4 `backend/learning/management/commands/` — comandi custom da terminale
Django permette di aggiungere comandi personalizzabili a `manage.py`. Qui ce ne sono due:
- **`importa_contenuti.py`**: `python manage.py importa_contenuti file.xlsx` — importa contenuti nel database (con opzione `--dry-run` per validare senza scrivere).
- **`valida_contenuti.py`**: `python manage.py valida_contenuti file.xlsx` — produce solo un report di validazione (errori e avvisi), usato anche dalla CI.

### 4.5 `backend/learning/migrations/`
Ogni volta che cambi `models.py` (es. aggiungi un campo), Django genera un file di **migrazione**: un piccolo script che descrive "come trasformare lo schema del database da uno stato al successivo". Le migrazioni si applicano con `python manage.py migrate` e vanno tenute in ordine cronologico (`0001_initial.py`, `0002_...py`, ecc.). Non si modificano mai a mano: si rigenerano con `makemigrations`.

### 4.6 `backend/learning/tests/`
Test automatici scritti con il framework di test di Django (basato su `unittest`). Coprono: autenticazione e permessi (`test_permissions.py`), profilo utente (`test_profile.py`), l'intero flusso lezione→quiz→punteggio (`test_pilot_lesson.py`), l'importazione idempotente (`test_commands.py`, `test_programma_workbook.py`) e le chiamate API end-to-end (`test_api.py`, `test_learning.py`). Si lanciano con `python manage.py test`.

### 4.7 `backend/fixtures/contenuti_minimi.json`
Un piccolo catalogo finto (3 lezioni con ID `DEMO-*`) usato solo per collaudare velocemente il motore in locale — non è contenuto editoriale reale.

### 4.8 `backend/sources/GRA-A1-001.json`
Sorgente JSON di una lezione reale pubblicata (formato "frammento singola lezione").

### 4.9 `backend/requirements.txt`
L'elenco delle librerie Python necessarie (Django, DRF, `corsheaders` per il CORS, `openpyxl` per leggere Excel, `psycopg` per parlare con Postgres, `gunicorn` come server di produzione). Si installano con `pip install -r requirements.txt`.

### 4.10 `backend/Dockerfile` e `.dockerignore`
Ricetta per costruire l'immagine Docker del backend: parte da un'immagine Python 3.13 leggera, installa le dipendenze, copia il codice e avvia `gunicorn` (un server di produzione, più robusto del server di sviluppo `runserver`).

### 4.11 `backend/db.sqlite3`
Il file fisico del database SQLite usato in sviluppo locale (creato/aggiornato da `manage.py migrate`).

---

## 5. Frontend (React) — file per file

### 5.1 `frontend/index.html`
La **singola pagina HTML** dell'intera app (da cui "Single Page Application"). Contiene solo uno scheletro con un `<div id="root">`: tutto il resto viene generato da JavaScript/React.

### 5.2 `frontend/src/main.jsx`
Il **punto d'ingresso** dell'app React: monta il componente `App` dentro `#root` e lo avvolge in `BrowserRouter` (gestisce la navigazione tra "pagine" senza ricaricare il browser).

### 5.3 `frontend/src/api.js`
Un piccolo helper che centralizza **tutte le chiamate all'API** del backend. Aggiunge automaticamente l'header di autenticazione (`Authorization: Token ...`) se l'utente ha fatto login, e trasforma gli errori HTTP in eccezioni JavaScript leggibili dai componenti.

```js
// Esempio semplificato di come viene usato altrove nel codice:
await api('/lezioni/GRA-A1-001/')                 // GET
await api('/auth/login/', { method: 'POST', body: JSON.stringify({...}) })  // POST
```

### 5.4 `frontend/src/App.jsx`
Il file più grande: contiene **tutti i componenti** dell'interfaccia (in un progetto più grande sarebbero divisi in più file). I concetti chiave per capirlo:

- **Componente** = una funzione JavaScript che ritorna JSX (una sintassi che assomiglia a HTML dentro il codice) e rappresenta un pezzo di interfaccia riutilizzabile (es. `LessonCard`, `QuizView`).
- **Stato (`useState`)** = una "variabile che, quando cambia, fa ridisegnare il componente". Es. in `QuizView`, `index` tiene traccia di quale domanda del quiz è mostrata.
- **Effetto (`useEffect`)** = codice che gira *dopo* che il componente è stato disegnato, tipicamente per andare a prendere dati dal server. `useLoad` (righe ~238) è un piccolo hook custom che incapsula il pattern "carica dati all'apertura della pagina, gestisci loading/errore".
- **Context (`AuthContext`)** = un modo per condividere dati (qui: l'utente loggato) tra componenti lontani nell'albero, senza doverli passare manualmente livello per livello.
- **Routing (`Routes`/`Route`)**: alla fine del file, la mappa URL → componente:
  - `/` → `HomePage`
  - `/lezioni` → `LessonsPage` (catalogo, pubblico)
  - `/lezioni/:id` → `LessonPage` (dettaglio lezione + quiz)
  - `/progressi`, `/profilo` → protette da `<Protected>` (richiedono login, altrimenti reindirizzano a `/login`)

Flusso tipico di una lezione (`LessonPage`, riga ~602):
1. Carica i dati della lezione con `useLoad(() => api('/lezioni/' + id + '/'))`.
2. Se la lezione è "in preparazione", mostra `InPreparationLesson` invece del contenuto.
3. Mostra le sezioni teoriche (`SectionList` → `Section`), poi l'area esercizi.
4. Se l'utente non è loggato, mostra un invito a registrarsi invece del quiz (`exercise-gate`).
5. Cliccando su un quiz si apre `QuizView`, che invia ogni risposta al backend per la verifica (mai calcolata solo lato client) e infine chiama `/quiz-finale/` per ottenere il punteggio ufficiale.

### 5.5 `frontend/src/styles.css` e `frontend/src/tokens.css`
Il CSS dell'app. `tokens.css` definisce le "variabili di design" (colori, spaziature, font) riutilizzate ovunque in `styles.css` — un pattern chiamato *design tokens*, utile per mantenere coerenza visiva e poter cambiare il tema in un solo posto.

### 5.6 `frontend/package.json`
L'equivalente di `requirements.txt` ma per JavaScript: elenca le dipendenze (`react`, `react-router-dom`, `vite`...) e gli **script** eseguibili con `pnpm <script>`:
- `pnpm dev` → avvia il server di sviluppo (ricarica automatica ad ogni modifica).
- `pnpm build` → genera i file statici ottimizzati per la produzione (cartella `dist/`).
- `pnpm test` → esegue i test con Vitest.

### 5.7 `frontend/Dockerfile` e `frontend/nginx.conf`
Il Dockerfile è "a due stadi": prima costruisce l'app React (`pnpm build`), poi copia solo il risultato finale (file statici) dentro un'immagine **nginx** (un server web leggerissimo per servire file statici). `nginx.conf` fa da "proxy": le richieste a `/api/` vengono inoltrate al backend Django, tutte le altre servono la SPA.

### 5.8 `frontend/design.md`
Note editoriali/di design del progetto (non codice).

---

## 6. Contenuti editoriali

### 6.1 `programma_lezioni_inglese_no_audio.xlsx`
Il "foglio di regia" del programma didattico: contiene l'elenco delle 98 lezioni, il percorso MVP (29 lezioni prioritarie), e i template di sezione per ogni area. **Non contiene ancora i testi definitivi** — quelli vengono scritti a mano in `lezioni_markdown/`.

### 6.2 `lezioni_markdown/`
Un file Markdown per lezione (organizzati per livello CEFR: A1, A2, B1, B2, C1 → area → file), scritti da un editor umano. Ogni file ha:
- un **frontmatter** (blocco `--- ... ---` a inizio file) con metadati come `id`;
- la teoria vera e propria;
- un esercizio guidato e un quiz finale con soluzioni.

`markdown_source.py` (visto sopra) legge questi file e li "pubblica" nel database uno alla volta.

- **`_schema.md`**: spiega la struttura che ogni brief deve rispettare.
- **`_indice.md`**: indice generale delle lezioni.
- **`_prompt_claude.md`**: istruzioni usate per generare/rivedere i contenuti con l'assistenza di un LLM.
- **`manifest.json`**: elenco macchina-leggibile delle lezioni presenti.

---

## 7. Docker e CI

### 7.1 `docker-compose.yml`
Descrive **tre servizi** che partono insieme con `docker compose up --build`:
1. `database` — PostgreSQL, con un controllo di salute (`healthcheck`) prima di far partire il resto.
2. `backend` — Django + gunicorn, aspetta che il database sia pronto, poi applica le migrazioni e parte.
3. `frontend` — build React servita da nginx, che fa da proxy verso il backend per le chiamate `/api/`.

Risultato: `http://localhost:8080` mostra il sito completo, senza dover installare Python o Node.js sulla propria macchina.

### 7.2 `.github/workflows/ci.yml`
Una pipeline di **Integrazione Continua**: ogni `push` o `pull request` su GitHub fa partire automaticamente due lavori paralleli:
- **backend**: installa le dipendenze, controlla che non manchino migrazioni, lancia tutti i test Django, valida il workbook Excel.
- **frontend**: installa le dipendenze e prova a fare la build di produzione.

Se qualcosa fallisce, il problema viene segnalato prima che il codice "rotto" venga considerato affidabile.

### 7.3 `.env.example`
Modello delle variabili d'ambiente necessarie in produzione (credenziali Postgres, chiave segreta Django, host consentiti). Si copia in un file `.env` reale (mai versionato) e si compila con valori veri.

---

## 8. Glossario minimo (per chi viene da Python "puro")

| Termine | Significato semplice |
|---|---|
| **API / endpoint** | Un "indirizzo" a cui il frontend manda una richiesta e riceve una risposta in JSON (es. `/api/lezioni/indice/`). |
| **ORM** | Un traduttore che ti fa scrivere `Lezione.objects.filter(...)` invece di SQL a mano; Django lo genera dai modelli in `models.py`. |
| **Migrazione** | Uno script che applica le modifiche di `models.py` alla struttura reale del database, mantenendo lo storico delle versioni. |
| **Token di autenticazione** | Una stringa segreta che il client (il browser) invia ad ogni richiesta per dimostrare "sono l'utente X, già loggato" — evita di rimandare email/password ogni volta. |
| **CORS** | Regola di sicurezza del browser che blocca richieste tra domini diversi a meno che il server non le autorizzi esplicitamente (fatto in `CORS_ALLOWED_ORIGINS`). |
| **Serializer** | Il "traduttore" tra oggetti Python e JSON, usato da Django REST Framework. |
| **Componente (React)** | Una funzione che descrive un pezzo di interfaccia e come reagisce quando i suoi dati cambiano. |
| **Hook (`useState`, `useEffect`)** | Funzioni speciali di React per gestire stato e "effetti collaterali" (come chiamate di rete) dentro un componente a funzione. |
| **DAG** | Grafo diretto senza cicli: qui modella "quali lezioni richiedono quali altre", garantendo che non ci siano dipendenze circolari impossibili da soddisfare. |
| **Idempotente** | Un'operazione che, ripetuta più volte con lo stesso input, dà sempre lo stesso risultato finale (l'importazione contenuti lo è: puoi rilanciarla senza creare doppioni). |
| **Transazione atomica** | Un blocco di operazioni sul database che va tutto a buon fine o viene annullato tutto insieme — mai uno stato "a metà". |

---

## 9. Come far girare tutto in locale (riepilogo pratico)

```bash
# 1. Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python manage.py migrate
python manage.py importa_contenuti fixtures/contenuti_minimi.json
python manage.py runserver          # API su http://localhost:8000/api/

# 2. Frontend (in un secondo terminale)
cd frontend
pnpm install
pnpm dev                            # sito su http://localhost:5173
```

Oppure, con Docker installato, un solo comando avvia tutto:

```bash
docker compose up --build           # sito su http://localhost:8080
```