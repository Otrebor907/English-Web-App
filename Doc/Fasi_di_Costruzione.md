# Fasi di costruzione — "Prima conversazione"

> Questo documento racconta **come è stata costruita** l'app, in ordine cronologico: quali decisioni sono state prese, in che ordine, e perché. Non ripete la spiegazione file-per-file — quella è già in [`Funzionamento.md`](Funzionamento.md), tienilo aperto come riferimento incrociato. Qui l'obiettivo è farti vedere **il processo**, così che tu possa continuarlo da solo o guidarlo consapevolmente.
>
> Fonte di questa ricostruzione: i 3 commit Git reali (`git log`) e il `CHANGELOG.md` del repository, che documenta un livello di dettaglio più fine (versioni 0.1.0 → 0.5.0) delle iterazioni avvenute **prima** che il lavoro venisse condensato nei commit. In altre parole: il codice è stato costruito a piccoli passi verificati, poi "fotografato" in commit più grandi.

---

## Fase 0 — Definire cosa costruire, prima di scrivere codice

Prima di qualunque riga di codice è stato fissato un **perimetro esplicito** (leggibile in `README.md` e nel `CHANGELOG.md`, sezione "Regole applicate"):

- una SPA (Single Page Application) testuale per adulti italiani che imparano l'inglese;
- percorso a **prerequisiti** (non un semplice elenco lineare di lezioni);
- contenuti divisi in 3 aree: Grammatica (GRA), Vocabolario (VOC), Comunicazione (COM);
- ogni lezione ha teoria + un esercizio guidato (non valutato) + un quiz finale (valutato, soglia 70%);
- **niente** audio, registrazione vocale, AI generativa nei contenuti, spaced repetition o drag&drop — esclusioni esplicite, per tenere lo scope stretto.

**Perché questo passaggio conta**: definire prima "cosa NON fare" ha evitato che il progetto si allargasse in feature non richieste. È la stessa logica che vale per qualunque progetto reale: uno scope scritto è quello che permette, più avanti, di dire "questo è fuori perimetro" invece di implementarlo per inerzia.

---

## Fase 1 — Fondamenta: scelta dello stack e primo scaffold

**Commit di riferimento**: `929b56a` — *Initial commit: MVP English learning SPA*.

### Le decisioni tecnologiche e il perché

| Livello | Scelta | Motivazione |
|---|---|---|
| Backend | **Python + Django** | Framework "batterie incluse": autenticazione, ORM, admin panel gratis, niente da scrivere da zero. |
| API | **Django REST Framework (DRF)** | Django da solo genera pagine HTML; DRF lo trasforma in un fornitore di JSON puro, consumabile da un frontend separato. |
| Frontend | **React + Vite** | React per un'interfaccia che si ridisegna da sola quando cambiano i dati; Vite come bundler/dev-server, molto più veloce di alternative più vecchie (Webpack). |
| DB sviluppo | **SQLite** | Un file singolo, zero configurazione — ideale per lavorare in locale. |
| DB produzione | **PostgreSQL** | Più robusto per un sito con utenti reali; il codice sceglie Postgres automaticamente se trova le variabili `POSTGRES_*` in `backend/config/settings.py`, altrimenti ripiega su SQLite. |

### Cosa è stato creato in questa fase

1. **Modello dati relazionale** (`backend/learning/models.py`): un `User` custom basato su email invece che username, tabelle "lookup" (`Area`, `Livello`, `StatoLezione`, ecc.) per vincolare i valori ammessi, `Lezione`, `Prerequisito` (relazione molti-a-molti), `SezioneLezione`, `Quiz`/`Quesito`, `Progresso`.
2. **Autenticazione a token DRF**: endpoint `register`/`login` che restituiscono un token, usato poi in ogni chiamata autenticata (`Authorization: Token ...`).
3. **API REST minime**: percorso lezioni, dettaglio lezione, avvio lezione, verifica quesito, invio quiz finale, progressi, profilo.
4. **Import contenuti**: un comando custom (`importa_contenuti`) capace di leggere un file JSON e scrivere tutto **in una transazione atomica** — o tutto si salva, o niente (nessuno stato intermedio corrotto).
5. **Frontend SPA**: routing con `react-router-dom` (`/percorso`, `/lezioni/:id`, `/progressi`, `/profilo`, `/login`, `/registrati`), un client HTTP centralizzato (`frontend/src/api.js`) che allega automaticamente il token.
6. **Docker + CI fin da subito**: `docker-compose.yml` (Postgres + Django/gunicorn + React/nginx) e una pipeline GitHub Actions (`.github/workflows/ci.yml`) che ad ogni push esegue test, controllo migrazioni e build.
7. **26 test automatici** già alla prima consegna — non un "aggiungeremo i test dopo".

**Perché costruire test e CI fin dal primo commit**: rimandare i test in un progetto che cresce è il modo più comune per ritrovarsi con codice che nessuno osa più toccare. Qui invece ogni fase successiva parte da una baseline di test verdi conosciuta (documentata puntualmente nel `CHANGELOG.md` prima di ogni intervento).

---

## Fase 2 — Il motore didattico: il grafo dei prerequisiti (DAG)

Il cuore logico dell'app non è l'interfaccia, è **la regola che decide quale lezione è sbloccata**. Questa regola vive in `backend/learning/services.py`:

- `collect_lesson_graph_errors` / `validate_lesson_graph`: verificano che il grafo dei prerequisiti sia un **DAG** valido (*Directed Acyclic Graph*) — niente cicli (A richiede B che richiede A), niente riferimenti a lezioni inesistenti, e ogni lezione pubblicata deve essere raggiungibile a partire dal nodo iniziale (la lezione con `ordine_mvp` più basso).
- `record_final_score`: salva il punteggio, marca la lezione completata se ≥ 70%, conserva sempre il **punteggio migliore**.
- Lo sblocco di una lezione richiede che **tutti** i prerequisiti siano completati (non un OR, un AND).

**Perché un DAG e non un semplice "lezione 1, 2, 3, ..."**: un percorso didattico reale non è quasi mai lineare (es. "il present perfect" può richiedere sia "past simple" sia "have got", indipendentemente). Modellarlo come grafo con validazione esplicita dei cicli evita che un errore editoriale (es. un prerequisito circolare inserito per sbaglio in un foglio Excel) blocchi silenziosamente l'intero percorso — la validazione fallisce rumorosamente invece di produrre un bug invisibile in produzione.

Questa fase ha prodotto anche la prima batteria di test dedicati esclusivamente al grafo: ciclo, ID inesistente, prerequisito fuori perimetro, nodo iniziale, raggiungibilità.

---

## Fase 3 — Hardening tecnico (CHANGELOG 0.3.0)

Con il motore funzionante, il passo successivo è stato **irrobustire** ciò che già esisteva, non aggiungere feature:

- Il validatore DAG è stato cambiato per raccogliere **tutte** le anomalie in un'unica esecuzione (prima probabilmente si fermava alla prima trovata) — utile per correggere un file editoriale con più errori in un solo giro invece di scoprirli uno alla volta.
- Aggiunto `importa_contenuti --dry-run`: valida senza scrivere nel database.
- Aggiunto `valida_contenuti`, con output leggibile da umani o JSON (pensato per la CI).
- Migliorato il Django Admin (filtri, ricerca, inline per prerequisiti/sezioni/quiz) — così i contenuti si possono ispezionare senza query manuali.
- Aggiunta un'API riservata allo staff e una pagina `/contenuti-da-completare` per il controllo editoriale.
- Prima passata di accessibilità: skip link, focus visibile, regioni live (`aria-live`), navigazione etichettata.
- Suite portata a 19 test.

**Perché questa fase esiste separatamente**: distinguere "far funzionare la cosa" da "renderla affidabile" è una disciplina utile. Qui si vede applicata: prima il DAG funzionava, poi è stato reso capace di segnalare *tutti* gli errori in un colpo solo, il che è un miglioramento di usabilità per chi scrive i contenuti, non per l'utente finale.

---

## Fase 4 — Collaudo reale nel browser e correzioni (CHANGELOG 0.3.1)

Con l'app avviabile, è arrivato il primo collaudo manuale nel browser, che ha fatto emergere bug invisibili nei soli test automatici:

- Bug di accesso API quando la SPA veniva aperta da `127.0.0.1` invece di `localhost` (i due host sono trattati come "origini" diverse dal browser per via del CORS).
- Fix: l'URL dell'API di sviluppo ora si adatta automaticamente all'hostname della pagina; le origini CORS locali di default includono entrambi.
- Bug di rendering: sezioni con un solo esempio generavano paragrafi HTML vuoti.
- Separazione più chiara tra navigazione "Percorso" e metadati nell'header della lezione.
- Collaudati manualmente: registrazione, sblocco, lezione, esercizio guidato, quiz finale, progressi, profilo — anche a 390px (viewport mobile stretto, uno degli standard di test responsive).

**Lezione di processo**: nessuna quantità di test automatici sostituisce il primo giro reale nel browser. Qui è stato fatto presto, non a fine progetto, quando i bug costano ancora poco da correggere.

---

## Fase 5 — Ampliamento del modello: priorità editoriali (CHANGELOG 0.4.0)

Con l'app stabile, è arrivato il primo vero **cambio di modello dati** dopo l'MVP iniziale:

- Aggiunto `Lezione.priorita` (P0 Essenziale, P1 Consigliata, P2 Secondaria, P3 post-MVP) — usato per **ordinare il lavoro editoriale**, mai la navigazione utente. *Rimosso in Fase 6: vedi sotto.*
- Vincoli applicativi e di database più stretti: solo le aree GRA/VOC/COM, `ordine_percorso` tra 1 e 98.
- Migrazione dati per pulire vecchi residui non più previsti (contenuti "PRN" legacy).
- Importatore esteso per rifiutare esplicitamente qualunque campo sorgente il cui nome contenga `audio` — un controllo automatico che rende impossibile reintrodurre per sbaglio un requisito escluso in Fase 0.
- Suite portata a 26 test.

**Perché distinguere `priorita` da `ordine_mvp`**: erano due concetti diversi — uno diceva "quanto è importante scrivere questo contenuto per primi" (lavoro editoriale), l'altro "in che ordine lo studente lo vede" (esperienza utente). In pratica `priorita` si è rivelato una copia 1:1 di `importanza_mvp` (P0=Essenziale, P1=Consigliata, P2=Secondaria, P3=nessuna): entrambi sono stati rimossi in Fase 6, lasciando `ordine_mvp` come unico ordinatore.

---

## Fase 6 — Integrazione del workbook Excel reale (CHANGELOG 0.2.0, poi consolidato)

A questo punto è arrivata la vera fonte editoriale: `programma_lezioni_inglese_no_audio.xlsx` (98 lezioni, percorso MVP di 29, template di sezione per area).

- `backend/learning/importer.py` è stato esteso con un parser nativo dei fogli `Programma Lezioni`, `Percorso MVP`, `Grammatica`, `Vocabolario`, `Comunicazione`, `Liste`.
- Il parser genera le sezioni marcate `TODO_FONTE` quando il testo definitivo non è ancora disponibile — **non vengono mai inventati contenuti didattici** per riempire il vuoto.
- Sono stati rilevati e documentati **due blocchi reali nella fonte** (non nel codice): un prerequisito fuori perimetro MVP (`GRA-A1-009 → GRA-A1-008`) e due "radici" del percorso senza prerequisiti (`GRA-A1-001` e `VOC-A1-001`), che rendono ambiguo il concetto di "lezione iniziale unica". Questi problemi sono stati segnalati come blocco nel changelog, non risolti forzando i dati.

**Perché questo è degno di nota**: quando l'importer trova un'incoerenza nella fonte editoriale (un foglio Excel scritto da una persona, non da un programmatore), il comportamento corretto non è "aggiustare silenziosamente i dati" ma **far fallire l'import con un messaggio chiaro**. Questo principio — validare rumorosamente piuttosto che correggere in silenzio — ricorre in tutta la costruzione del progetto ed è visibile ancora oggi nell'importer.

---

## Fase 7 — Slice pilota: sicurezza, stato "in preparazione", navigazione a sezioni

**Commit di riferimento**: `3f4098f` — *Slice pilota GRA-A1-001: sicurezza, stato in preparazione, navigazione sezioni*.

Con 98 lezioni nel database ma **zero pubblicate** (tutte in stato "Da sviluppare"), si è deciso di concentrarsi su **una sola lezione pilota** (`GRA-A1-001`) end-to-end, invece di procedere a tappeto. Prima di tutto è stata fatta una revisione dello stato esistente (sezione "REVIEW CLAUDE" del changelog), che ha isolato tre problemi P0:

1. **Falla di sicurezza**: l'endpoint `check_answer` (verifica di un singolo quesito) non filtrava per lezioni pubblicate. Un utente autenticato che conoscesse l'ID di un quesito appartenente a una lezione ancora in bozza poteva ottenerne risposta corretta e spiegazione. Fix: stesso filtro (`stato_id="PUBBLICATA"`) già usato dagli altri endpoint.
2. **Ambiguità sui dati**: la fixture tecnica di test usava per coincidenza gli stessi ID (`GRA-A1-001` ecc.) del catalogo editoriale reale. Rinominata in un namespace esplicito `DEMO-*`, per non rischiare che qualcuno confondesse contenuti demo con contenuti reali.
3. **Copertura test mancante** su un percorso di errore già gestito ma mai testato.

Poi, sulla base di questa revisione, sono state implementate le feature della slice:

- Nuovo stato utente **"in preparazione"**: `path_lessons` ora espone anche le lezioni MVP non ancora pubblicate, con un flag dedicato; la card è visibile ma non apribile. Gli endpoint sensibili (`/inizia/`, `/quiz-finale/`) restano 404 su di esse.
- **`SectionCarousel`**: navigazione di una lezione sezione-per-sezione (invece di tutto impilato), con progress bar accessibile (`role="progressbar"`) e gestione del focus tastiera.
- **`QuizView`** rifatto: banner esplicito per distinguere esercizio guidato (non valutato) da quiz finale (valutato), gestione del caso "quiz vuoto", focus management al cambio domanda.
- 13 nuovi test dedicati, portando la suite a **39/39 verdi**.

**Perché una "slice" e non tutte le 98 lezioni insieme**: verificare l'intero flusso (sicurezza, stati, UI, accessibilità) su una sola lezione reale prima di ripetere il pattern altrove riduce il rischio di propagare un errore di design a 98 casi contemporaneamente. È lo stesso principio di "iterare in piccolo e verificare" già visto nelle fasi precedenti.

---

## Fase 8 — Redesign completo e contenuti editoriali reali (Hallmark "Hum")

**Commit di riferimento**: `3283c29` — *Redesign playful (Hallmark Hum), sicurezza percorso e contenuti A1-C1* (il più recente, oggi).

Questa è la fase più ampia finora, con tre filoni paralleli:

### 8.1 — Design system

È stato introdotto un design system esplicito e documentato in [`frontend/design.md`](../frontend/design.md), col nome in codice **"Hum"**: tema "vivace/vivo", palette a tre accenti in OKLCH (giallo-pera primario, ciano secondario, corallo per un unico momento ad alta energia per pagina), tipografia Plus Jakarta Sans + JetBrains Mono, spaziature a scala nominale in `tokens.css`. Ogni famiglia di schermate (Auth, Percorso, Lezione, Progressi/Profilo) ha una "macrostruttura" propria invece di un layout generico ripetuto ovunque — una scelta esplicita per evitare l'aspetto "template generico" tipico di interfacce generate velocemente.

Tecnicamente questo si è tradotto in: nuovo file `frontend/src/tokens.css` (89 righe di variabili di design), riscrittura sostanziale di `App.jsx` (+506 righe) e `styles.css` (quasi raddoppiato), nuova `HomePage` pubblica, `LessonSidebar` con indice completo per area, nuovo endpoint dedicato `/api/lezioni/indice/`.

### 8.2 — Cambio di semantica del percorso

Una decisione di prodotto importante: **il blocco "duro" del DAG è stato rimosso**. Prima, una lezione con prerequisiti non completati risultava `BLOCCATA` e non era in alcun modo raggiungibile lato API. Ora:

- `lesson_state` non restituisce più lo stato `BLOCCATA`;
- i prerequisiti restano un **ordine consigliato**, non un cancello che impedisce l'accesso;
- `mark_in_progress` e `record_final_score` non sollevano più errore se mancano i prerequisiti;
- è stato aggiunto `Progresso.assegnata` (migrazione `0003`) per distinguere le lezioni assegnate al percorso personale dell'utente da quelle semplicemente visibili nel catalogo.

**Perché questo cambio**: è tipico che, testando un MVP con blocco rigido, ci si accorga che per un pubblico adulto che studia in autonomia un cancello troppo rigido frustra più di quanto aiuti — meglio suggerire un ordine e lasciare la libertà di saltare. Questo è un esempio di come una regola di dominio, anche se tecnicamente ben implementata (Fase 2), può comunque essere sbagliata come *scelta di prodotto* e va rivista quando emergono nuove informazioni.

### 8.3 — Contenuti editoriali reali per 98 lezioni

È stata creata la cartella `lezioni_markdown/`, organizzata per livello CEFR (A1 → C1) e area, con un file Markdown per lezione: bozze reali di grammatica, vocabolario, comunicazione, più un `manifest.json` macchina-leggibile, un indice (`_indice.md`), uno schema (`_schema.md`) e un prompt di riferimento (`_prompt_claude.md`) usato per generare/rivedere i contenuti con assistenza di un LLM.

È stato scritto un nuovo modulo, `backend/learning/markdown_source.py`, e un comando dedicato, `backend/learning/management/commands/pubblica_da_markdown.py`, che legge questi brief e pubblica **una lezione alla volta** senza toccare le altre — coerente con l'approccio "slice" già visto in Fase 7.

Sono stati aggiunti anche `test_permissions.py` e `test_profile.py` per coprire i nuovi comportamenti di sicurezza e stato.

---

## Stato attuale del progetto (a oggi, 2026-07-23)

Cosa è **completo e testato**:
- Backend Django/DRF con modello dati, autenticazione, API REST, admin, import atomico e idempotente da JSON/Excel/Markdown.
- Motore di percorso (ordine consigliato, non più a blocco rigido) con quiz testuali valutati lato server.
- Frontend React/Vite con design system proprio, navigazione a sezioni, quiz accessibile.
- Docker Compose (Postgres + Django/gunicorn + React/nginx) e CI GitHub Actions su ogni push.
- Suite di test in crescita continua (26 → 39 → più test di permessi/profilo nell'ultima fase).

Cosa **manca ancora** (i "TODO fonte" espliciti, mai aggirati inventando contenuti):
- I testi definitivi e i quiz per la maggior parte delle 98 lezioni — le bozze in `lezioni_markdown/` sono un lavoro in corso, non tutte ancora pubblicate nel database.
- Le due "radici" del percorso MVP (`GRA-A1-001` e `VOC-A1-001`) restano una decisione editoriale aperta su come collegarle.
- Aspetti espliciti "fuori scope MVP" e rimandati a produzione: policy password più robusta (`AUTH_PASSWORD_VALIDATORS` vuoto), `SECRET_KEY` di sviluppo da sostituire, rate limiting su login/registrazione, paginazione se il catalogo crescerà molto oltre le 29 lezioni MVP attuali.

---

## Come continuare da qui (consigli pratici)

Se vuoi portare avanti l'app da solo, questi sono i punti d'ingresso più naturali, in ordine di impatto:

1. **Pubblicare altre lezioni reali**: scrivi un file Markdown in `lezioni_markdown/<livello>/<area>/` seguendo lo schema in `_schema.md`, poi lancia `python manage.py pubblica_da_markdown <id-lezione>`. Questo è il modo previsto per far crescere il catalogo senza toccare codice.
2. **Verificare sempre con i test dopo ogni modifica**: `python manage.py test -v 2` (backend) e `pnpm build` (frontend) — la disciplina di questo progetto è di non considerare "fatto" nulla che non sia verde su entrambi.
3. **Prima di cambiare un modello** (`models.py`), genera la migrazione con `python manage.py makemigrations` e falla girare con `migrate` — non modificare mai a mano una migrazione già creata.
4. **Se aggiungi una regola di business** (es. nuove condizioni di sblocco), scrivila in `services.py`, non dentro le viste (`views.py`) — è il pattern seguito finora per tenere la logica testabile separatamente dall'endpoint HTTP.
5. **Per modifiche visive**, consulta prima `frontend/design.md`: è pensato per essere lo standard unico a cui ogni nuova schermata deve aderire, invece di inventare uno stile diverso pagina per pagina.
6. **Produzione**: quando sarai pronto a mettere online l'app, riprendi la lista "cosa manca" sopra (password policy, secret key, rate limiting) prima di esporla pubblicamente — sono gli unici punti esplicitamente rimandati per scelta, non dimenticati.

Per il dettaglio di ogni singolo file e per un glossario dei termini tecnici (API, ORM, migrazione, token, CORS, DAG...), il riferimento resta [`Funzionamento.md`](Funzionamento.md).

---

## Fase 6 — Refactoring dello schema (migration `learning.0006`)

Allineamento dei nomi al ruolo effettivo delle tabelle e riduzione delle ridondanze emerse dall'analisi dei dati.

**Tabelle di mapping.** `learning_area`, `learning_tipologia`, `learning_livello` e `learning_difficolta` non sono tassonomie ma mapping codice→etichetta, e ora si chiamano `mapping_area_lezione`, `mapping_tipologia`, `mapping_livello`, `mapping_difficolta_lezione`. I nomi delle classi Python non cambiano: la rinomina passa da `Meta.db_table`, così il codice applicativo resta invariato.

**Ridondanze rimosse.** `learning_lezione.priorita` e la tabella `learning_importanza` erano la stessa informazione scritta due volte (l'importer derivava letteralmente l'una dall'altra). Entrambe eliminate. L'ordinamento editoriale ora usa `ordine_mvp`.

**Strutture rinominate.** `learning_sezionelezione` → `struttura_lezione`, `learning_quiz` → `struttura_quiz`: i nomi dicono cosa contengono.

**Quesiti separati.** `learning_quesito` è diventata `struttura_quiz_guidato` e `struttura_quiz_finale`. Le colonne sono identiche e restano allineate tramite la classe base astratta `QuesitoBase`. **Conseguenza sull'API**: gli `id` non sono più univoci fra le due tabelle, quindi la rotta di verifica è passata da `/api/lezioni/<id>/quesiti/<qid>/verifica/` a `/api/lezioni/<id>/quiz/<modalita>/quesiti/<qid>/verifica/`. Il payload della lezione non cambia: `QuizSerializer` continua a esporre i quesiti sotto la chiave `quesiti`.

**Perché `Prerequisito` è rimasta.** Era previsto di sostituirla con un prerequisito derivato dall'ID (`GRA-A1-018` → `GRA-A1-017`). La regola è stata verificata su tutti i 119 archi e riproduce il dato in 64 casi su 96: non copre le 22 lezioni con prerequisiti multipli, i 18 archi fra aree diverse, né le 15 lezioni con suffisso `-001`; in un caso inverte la dipendenza. Eliminarla avrebbe perso 55 archi e reso inutilizzabile la validazione del DAG in `services.py`. La logica esiste comunque come `Lezione.prerequisito_derivato`, un campo calcolato che non tocca lo schema.

---

## Fase 7 — Semplificazione dello schema (migration `learning.0007`, `0008`, `0009`)

Fase di sfoltimento, non di costruzione: togliere dallo schema tutto ciò che non serve al prodotto che si sta avviando. La complessità si reintroduce quando c'è un motivo, su un prodotto già vivo.

**Permessi granulari di Django rimossi** (`0007`). `User` ereditava da `AbstractUser`, che porta con sé `PermissionsMixin` e quindi due tabelle ponte, `learning_user_groups` e `learning_user_user_permissions`. Non erano mai state usate: l'unica distinzione che il progetto fa è `is_staff` / `is_superuser`. `User` ora eredita da `AbstractBaseUser` e dichiara a mano quei booleani più `has_perm()` / `has_module_perms()`, che l'admin di Django richiede. Rimossa anche `date_joined`, doppione di `creato_il`. La pagina "Gruppi" è stata tolta dall'admin: senza il campo `groups` non avrebbe alcun effetto.

**Tabelle dimensione** (`0008`). Le cinque tabelle codice→etichetta prendono il prefisso `dim_`: `dim_area_lezione`, `dim_tipologia`, `dim_livello`, `dim_difficolta_lezione`, `dim_stato_lezione` (quest'ultima era ancora `learning_statolezione`). Minuscolo di proposito — Postgres abbassa gli identificatori non virgolettati, quindi `SELECT * FROM dim_livello` funziona senza virgolette, mentre `DIM_livello` avrebbe imposto le virgolette in ogni query scritta a mano.

**`fase_roadmap` eliminata** (`0008`). Aveva due soli valori sui dati reali, `"Fase 1 — MVP"` e `"TODO_FONTE"`, e coincideva esattamente con l'avere o meno `ordine_mvp`. La stessa informazione era già in `stato_id` (`DA_SVILUPPARE`, `DA_SVILUPPARE_MVP`, `PUBBLICATA`). Scritta in tre posti, ora in uno.

**Il grafo dei prerequisiti eliminato** (`0008`). Via la tabella `learning_prerequisito`, la M2M `Lezione ↔ Lezione` che le stava sopra, il campo calcolato `prerequisito_derivato`, la validazione del DAG in `services.py` (`collect_lesson_graph_errors`, `validate_lesson_graph`), `missing_prerequisites`, le chiavi `prerequisiti_mancanti` e `prerequisiti_consigliati` nell'API, il «Segue X» nel frontend e i test dedicati (`test_graph.py`).

Perché: dalla Fase 4 i prerequisiti non bloccavano più nulla — erano diventati un consiglio, e nessuna lezione era mai inaccessibile. Restava quindi un grafo con validazione DAG, una tabella ponte e una colonna nel workbook per produrre un suggerimento di navigazione. L'ordine con cui affrontare le lezioni resta espresso da `ordine_mvp` (1..29 sul percorso MVP) e `ordine_percorso` (1..98 sul programma completo), che è ciò che il sito usa davvero per ordinare l'indice.

Questa fase corregge esplicitamente la decisione presa in Fase 6 (*"Perché `Prerequisito` è rimasta"*): quell'analisi era corretta sui dati — la regola derivata dall'ID copriva solo 64 archi su 96 — ma rispondeva alla domanda sbagliata. Non era «come conserviamo i 119 archi», era «a cosa servono». La risposta, per l'MVP, è: a niente.

**Tabelle dell'utente rinominate** (`0009`). `learning_user` → `user_profile`, `learning_progresso` → `user_progress`. Insieme al prefisso `dim_` delle tabelle dimensione, lo schema su Neon si legge ora per famiglie: `dim_*` i codici, `struttura_*` i contenuti editoriali, `user_*` ciò che appartiene a chi usa il sito.

**`minuti_effettivi` eliminata** (`0009`). La colonna veniva incrementata dal parametro `minuti` di `submit_final_quiz`, che il frontend non ha mai inviato: valeva `0` su tutte le righe. Rimossa insieme al parametro `minutes` di `record_final_score()`.

**Django Admin rimosso, e con lui cinque tabelle di infrastruttura.** `auth_group`, `auth_group_permissions` e `auth_permission` erano rimaste dopo la `0007`: non appartengono al modello dati del progetto ma a `django.contrib.auth`, e finché quell'app è installata esistono. Verificato che non c'è via di mezzo — togliere `django.contrib.auth` tenendo l'admin fallisce con `RuntimeError: Model class django.contrib.auth.models.Permission ... isn't in an application in INSTALLED_APPS`, perché l'admin è costruito sopra quel sistema di permessi.

Scelta: rimuovere il pannello. Il flusso reale di pubblicazione passa da `pubblica_da_markdown` e `importa_contenuti`, non dall'admin, e i dati si ispezionano dall'editor SQL di Neon. Disinstallate `django.contrib.admin`, `auth`, `contenttypes`, `sessions` e `messages`; eliminati `learning/admin.py`, la rotta `admin/` e i middleware/context processor che le servivano. Su Neon sono state eliminate `auth_group`, `auth_group_permissions`, `auth_permission`, `django_admin_log`, `django_content_type` e `django_session`, più le righe di `django_migrations` delle app disinstallate: **da 20 tabelle a 14**.

Due pezzi di `django.contrib.auth` erano però in uso e sono stati riscritti in casa:

- `authenticate()` → `services.authenticate_by_email()`. Replica `ModelBackend`, compresa la difesa contro il timing attack: se l'email non esiste calcola comunque un hash, altrimenti una risposta molto più rapida rivelerebbe quali email sono registrate.
- `AnonymousUser` → `learning/auth.py`. DRF lo mette in `request.user` a ogni richiesta senza token; il default punta a `django.contrib.auth.models`, non più importabile. Aggancio via `REST_FRAMEWORK["UNAUTHENTICATED_USER"]`.

**La `0001_initial` è stata modificata a mano**, contro la regola generale di non toccare le migrazioni già applicate. Il motivo: dichiarava `dependencies = [("auth", "0012_...")]` e creava i campi `groups` / `user_permissions` con `to="auth.group"`. Con `auth` fuori da `INSTALLED_APPS` quel nodo non esiste più nel grafo e **un database creato da zero non sarebbe partito** — i test compresi. Rimossa la dipendenza e i due campi, e tolte per coerenza le `RemoveField` corrispondenti dalla `0007`. Lo schema finale è identico e su un database già migrato non cambia nulla.

**Conseguenza operativa da ricordare:** non esistono più i comandi `createsuperuser` e `changepassword`, che arrivavano da `django.contrib.auth`. Per creare un amministratore: `python manage.py shell -c "from learning.models import User; User.objects.create_superuser(email='...', password='...')"`.

**Il token di sessione in tabella propria** (`0010`). `authtoken_token` era l'ultima tabella fuori dallo schema di nomi, e apparteneva a `rest_framework.authtoken`. DRF prevede l'estensione: il suo modello `Token` diventa astratto quando l'app non è in `INSTALLED_APPS` (`abstract = 'rest_framework.authtoken' not in settings.INSTALLED_APPS` nel suo `Meta`), quindi lo si eredita cambiando solo `db_table`. Aggiunti `learning.models.Token` (tabella `user_authtoken_token`) e `learning.auth.TokenAuthentication`, che punta DRF al modello nuovo.

La migrazione crea la tabella e poi travasa le righe **solo se** trova la vecchia: su Neon i 9 token esistenti sono stati spostati e restano validi (nessun utente è stato disconnesso), mentre su un database creato da zero `authtoken_token` non esiste nemmeno, perché l'app che la creava non è più installata.

**Risultato della Fase 7: da 20 tabelle a 14**, e le uniche due che non appartengono al dominio sono `django_migrations` e `learning_lezione` — quest'ultima è l'unica rimasta col vecchio prefisso `learning_`, in mezzo a `dim_*`, `struttura_*` e `user_*`.
