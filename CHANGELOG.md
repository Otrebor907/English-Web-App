# Changelog

## REVIEW CLAUDE — STATO INIZIALE — 2026-07-22

Revisione integrale eseguita prima di qualunque modifica. Baseline ripetuta e confermata:

- `python manage.py test -v 2` → **26/26 verdi**.
- `python manage.py check` → **0 problemi**.
- `python manage.py makemigrations --check --dry-run` → **nessuna modifica rilevata**.
- `python manage.py valida_contenuti ../programma_lezioni_inglese_no_audio.xlsx --json` → **valido**: 98 lezioni, 29 MVP, 119 prerequisiti, 824 sezioni TODO, 0 quiz, priorità P0=13/P1=11/P2=5/P3=69; avvisi noti (2 radici MVP, 0 lezioni pubblicate, quiz mancanti, normalizzazione GRA-A1-008).
- **`pnpm build` non eseguibile in questo ambiente**: `node`, `npm` e `pnpm` non sono installati sul Mac. Esiste `frontend/node_modules/.bin/vite` e `frontend/dist/` da un ambiente precedente. Non posso fare `pnpm dev` né aprire il browser sull'app viva. Segnalato come blocco di collaudo (non di codice).

### Lavoro non verificato dall'handoff

- **`backend/sources/GRA-A1-001.json`**: solo metadati della lezione pilota. Non ha `obiettivo_didattico`, `competenze`, `durata_min`, `errori_tipici`, `stato`. Se passato a `importa_contenuti` viene respinto da `_reject_incomplete_json_fragment` con messaggio esplicito. **Non è né una fixture né una fonte importabile**: è un *pro-memoria* dei metadati. Utile come esempio didattico dell'errore che l'importer emette; da tenere ma da coprire con test.
- **`_reject_incomplete_json_fragment`** in `backend/learning/importer.py`: disegno corretto (solo `dict` con `id` ma senza `lezioni` triggera; non tocca i workbook Excel; messaggio elenca campi mancanti + blocchi catalogo mancanti). **Nessun test lo copre**. Verrà coperto in Fase 2.

### Problemi P0 (correggere subito nella slice pilota)

- **[SICUREZZA] `check_answer` non filtra su `stato_id="PUBBLICATA"`.** In `backend/learning/views.py:91` il quesito è recuperato via `quiz__lezione_id=lesson_id`, senza restringere alle sole lezioni pubblicate. Un utente autenticato che conosca l'id di un quesito di una lezione in bozza può interrogarlo e ricevere `risposta_corretta` e `spiegazione`. `submit_final_quiz` e `start_lesson` già filtrano; questo endpoint è l'unica eccezione. Fix: stesso pattern degli altri (`ordine_mvp__isnull=False`, `stato_id="PUBBLICATA"`).
- **[DATI/CHIAREZZA] Sovrapposizione ID fra fixture tecnica e lezione pilota reale.** In `backend/fixtures/contenuti_minimi.json` `GRA-A1-001` è la demo "Il verbo essere: to be". Nel workbook editoriale `GRA-A1-001` è "L'ordine delle parole: Soggetto + Verbo + Oggetto". Rischio concreto di confusione operativa: chi lavora sulla lezione pilota reale potrebbe leggere/ereditare contenuti demo. Fix: rinominare gli ID della fixture in un namespace `DEMO-*` esplicitamente tecnico e aggiornare i test.
- **[TEST MANCANTE] `_reject_incomplete_json_fragment` senza copertura.** Va aggiunto almeno un test che, dato `backend/sources/GRA-A1-001.json`, verifica che `load_source`/`importa_contenuti` falliscono con messaggio esplicito e che il database resta invariato.

### Problemi P1 (importanti per la slice pilota)

- **[UX/CONTENUTI] Nessuno stato "contenuto in preparazione" nella dashboard.** Oggi `path_lessons` filtra `stato_id="PUBBLICATA"`. Il workbook reale non pubblica nessuna lezione MVP; l'utente non vede nulla di reale. Fix: `path_lessons` include anche le lezioni MVP con `stato_id="DA_SVILUPPARE"`, ognuna con flag `in_preparazione=True`; card mostrata ma non apribile, badge "in preparazione". `lesson_detail` continua a restituire 404 su non pubblicate (o meglio, un 200 con solo metadati e flag `in_preparazione`, per servire una pagina dedicata).
- **[UI PILOTA] La `LessonPage` non ha indicatore di avanzamento fra sezioni, né navigazione sezione-per-sezione.** Tutte le sezioni sono impilate; l'utente non ha un senso di progresso durante la lezione. Requisito esplicito della slice.
- **[UI] `LessonPage` chiama silenziosamente `POST /lezioni/:id/inizia/` a ogni caricamento** (`.catch(() => {})`). Un fallimento non è mai visibile e la lezione già completata viene comunque marcata `in_corso`. Il backend protegge da regressione (`if progress.stato != COMPLETATA`), quindi non c'è danno, ma il pattern è opaco.
- **[QUIZ] `QuizView` non gestisce il caso "quiz mancante"** (`lesson.quiz.length === 0`): nella slice si serve una lezione con contenuti in preparazione o senza quesiti reali. Serve messaggio "quiz in preparazione".
- **[QUIZ/UX] Il pulsante "Verifica" resta disabilitato solo su `!answer`**, ma dopo verifica il flusso richiede di premere manualmente "Continua"; non c'è indicazione tastiera-only o `aria-live` progressiva sull'avanzamento fra domande.
- **[A11Y] Il feedback nella dashboard ("Prima completa: …") ha colore ambra su fondo chiaro con contrasto marginale.** Va portato su un colore accessibile (WCAG AA).
- **[A11Y] Ordine dei tab e focus quando cambia il quesito**: dopo `setIndex(index + 1)` il focus resta sul pulsante "Continua", che è appena stato smontato → il focus torna al body. Va gestito (focus al nuovo `<h3>` del quesito).

### Problemi P2 (importanti ma fuori slice pilota — annotati, non tutti risolti ora)

- **[MODELLO] Default `Progresso.stato = DISPONIBILE`.** Quando `Progresso` viene creato per la prima volta, il default è disponibile: la logica di `sync_progress` compensa, ma per una `Lezione` con prerequisiti non ancora completati e senza sync (es. `mark_in_progress` su una lezione libera che ne blocca un'altra), lo stato iniziale corretto non è garantito. `sync_progress` è chiamato prima di ogni `path_lessons` e `progress_list`, quindi in pratica non è un bug; ma il default non riflette la realtà del DAG. Annotare come debito.
- **[SICUREZZA/PROD] `AUTH_PASSWORD_VALIDATORS = []`.** Fuori scope dello slice pilota; già segnalato in `README` come lavoro di produzione.
- **[SICUREZZA/DEBUG] `SECRET_KEY = "dev-only-change-me"` di default.** Ok in dev, va imposto in prod.
- **[VIEWS] Nessuna paginazione su `path_lessons` e `progress_list`.** Con 29 lezioni MVP è accettabile; da rivedere se la pubblicazione crescerà.
- **[IMPORTER] `import_content` elimina prima e riscrive (`SezioneLezione.objects.all().delete()` + `bulk_create`).** Idempotente ma non incrementale: perde ordine se un import parziale succede a metà transazione (transazione atomica → ok in pratica). Annotare.

### Rischi di integrità dati

- **Confusione fixture ↔ reale** — coperto sopra (P0).
- Il modello `Lezione.stato` è FK a `StatoLezione`, quindi non è vincolato a priori a un insieme chiuso di stati; la logica applicativa presume `PUBBLICATA` e `DA_SVILUPPARE`. Se una lookup di stato viene rinominata, la logica delle view si rompe silenziosamente. Non risolvibile senza refactor: annotato.

### Problemi importer

- Corretto e ben testato per JSON/Excel completi.
- **Manca copertura test** su `_reject_incomplete_json_fragment` (P0).
- Nessun bug rilevato nel loop del workbook editoriale.

### Problemi API / sicurezza

- **P0**: `check_answer` non filtra pubblicata (sopra).
- I quesiti in `QuestionSerializer` non espongono `risposta_corretta` — corretto.
- `LessonDetailSerializer` non espone risposte corrette — corretto.
- Nessun rate limit su login/register: fuori scope MVP.

### Problemi React / stato

- `LessonPage` chiama `/inizia/` in silenzio (P1 sopra).
- `QuizView` non resetta lo scroll / focus al nuovo quesito.
- Nessuna gestione visiva di "quiz mancante".
- Il quiz `guidato` in `QuizView` mostra "ESERCIZIO GUIDATO · NON FA PUNTEGGIO" solo come eyebrow: non c'è un banner chiaro né una separazione visiva rispetto al quiz finale.

### Problemi UX / responsive / accessibilità

- Nessun indicatore di avanzamento fra sezioni (P1).
- Focus non spostato quando cambia il quesito (P1).
- Requisiti "prima completa" a basso contrasto (P1).
- A 390 px la lesson-hero occupa oltre 300 px verticali prima del contenuto: buono per identità visiva ma penalizza il primo scroll. Accettabile, da valutare.
- L'header nasconde `.lesson-order` su mobile: perde il senso di posizione nel percorso.

### Test mancanti (da aggiungere in Fase 2)

- Riconoscimento e rifiuto del frammento JSON `sources/GRA-A1-001.json` (P0).
- Fixture usa ID `DEMO-*`, cioè: nessuna lezione pubblicata della fixture ha ID reali (es. `GRA-A1-001`) — sono separati.
- Endpoint `check_answer` blocca lezioni non pubblicate.
- `lesson_detail` e `start_lesson` restituiscono 404 su lezioni non pubblicate (già di fatto testato in modo trasversale; test dedicato utile).
- Path espone lezioni "in preparazione" con flag corretto.
- Esercizio guidato non aggiorna `Progresso.punteggio`.
- Miglior punteggio conservato (già coperto — mantenere).
- Assenza campi audio e area PRN (già coperto — mantenere).

### Codice incompleto o incoerente

- `backend/sources/GRA-A1-001.json`: metadati parziali, coerenti col workbook ma non importabili. Verrà tenuto come esempio di frammento, coperto da test.
- Nessun contenuto didattico definitivo per la lezione pilota. **Non verranno inventati.**

### Piano d'azione per la slice pilota (Fase 2)

1. Fix P0 sicurezza `check_answer`.
2. Rinominare la fixture: `GRA-A1-001` → `DEMO-GRA-001`, `VOC-A1-001` → `DEMO-VOC-001`, `COM-A1-001` → `DEMO-COM-001`. Aggiornare i test.
3. Aggiungere il flag "contenuto in preparazione": `path_lessons` include lezioni MVP con `stato_id="DA_SVILUPPARE"` con badge dedicato; `lesson_detail` risponde 200 con solo metadati + flag su queste; l'apertura mostra pagina "in preparazione". Le lezioni PUBBLICATE mantengono il comportamento attuale.
4. Componente riutilizzabile `❌ → ✅ → perché` già presente (`ErrorBox`): consolidare, esportare, migliorare accessibilità e contrasto.
5. UI slice pilota: navigazione sezione-per-sezione con indicatore di avanzamento, focus management al cambio quesito, banner esplicito guidato vs finale, stato "quiz in preparazione".
6. Contenuti mancanti per pubblicare davvero GRA-A1-001 (TODO da chiedere a te — non verranno inventati).
7. Test obbligatori aggiunti.

### Contenuti che mi devi fornire per pubblicare davvero GRA-A1-001

Il workbook fornisce, per `GRA-A1-001` — "L'ordine delle parole: Soggetto + Verbo + Oggetto":

- Nome, descrizione ("Regola spiegata in parole semplici…"), obiettivo didattico ("Costruire frasi inglesi rispettando l'ordine fisso SVO…"), competenze ("Grammatica, Lettura"), durata (12 min), errori tipici ("Frasi senza soggetto…"; "aggettivo dopo il nome…"), stato "Da sviluppare (MVP)".
- Struttura editoriale delle 9 sezioni (Obiettivo, Regola e quando si usa, Struttura, Esempi con traduzione, Errori tipici degli italiani, Confronto con forme simili, Esercizio guidato, Esercizio finale, Riepilogo e prossima lezione), ognuna con `Contenuto Previsto` e `Formato Web App`.

Mancano i contenuti definitivi che non inventerò:

1. **Sezione 1 — Obiettivo**: la frase concreta "Alla fine saprai…" da mostrare come banner (1 riga).
2. **Sezione 2 — Regola e quando si usa**: definizione breve, contesti d'uso, confronto con l'italiano (3–6 righe).
3. **Sezione 3 — Struttura**: tabella affermativa/negativa/interrogativa con eventuali eccezioni (una tabella di 3 righe, o schema).
4. **Sezione 4 — Esempi con traduzione**: 6–8 esempi inglesi + traduzione italiana + parole chiave da evidenziare.
5. **Sezione 5 — Errori tipici degli italiani**: 3–5 triplette ❌ frase sbagliata → ✅ frase corretta → perché.
6. **Sezione 6 — Confronto con forme simili**: 2–4 righe di comparazione (SVO vs ordine italiano più libero, posizione aggettivo, ecc.).
7. **Sezione 7 — Esercizio guidato**: 3–5 quesiti misti (scelta_multipla o completamento) con feedback immediato e spiegazione. Modalità `guidato`, non aggiorna punteggio.
8. **Sezione 8 — Esercizio finale (quiz)**: 8–10 quesiti misti (scelta_multipla e/o completamento) con `risposta_corretta` e `spiegazione` per ciascuno. Modalità `finale`, soglia 70%.
9. **Sezione 9 — Riepilogo e prossima lezione**: bullet di 3–5 punti di ricapitolazione; il rimando alla lezione successiva viene già dal DAG.

Fino a quando questi contenuti non arrivano, la lezione pilota reale `GRA-A1-001` resta con stato `Da sviluppare (MVP)` e la SPA la mostra come "Contenuto in preparazione" (card visibile, non apribile).

### ASSUNZIONI in vigore (aggiornate)

- Fixture demo con namespace `DEMO-*`: ordini di percorso 1..3, priorità P0, stato PUBBLICATA. Serve solo per test tecnici e per collaudo del motore, mai come contenuto pubblicato.
- Lezioni MVP con stato sorgente "Da sviluppare (MVP)" sono ammesse nel `path_lessons` con flag `in_preparazione=True`. Nessuna api sensibile è raggiungibile su di esse (quiz, verifica risposte, inizio).
- Non verranno inventati testi, esempi, traduzioni, esercizi o quiz. Le lezioni con contenuti mancanti mostrano lo stato "Contenuto in preparazione".
- L'ambiente locale non ha Node/pnpm: `pnpm build` e collaudo browser non sono eseguibili qui. Il codice frontend viene modificato ma non collaudato nel browser in questa passata; il collaudo umano sul browser va fatto sulla tua macchina.

## 0.5.0 — 2026-07-22 — Slice pilota GRA-A1-001 revisionata

Chiude la revisione di 2026-07-22. Copre solo la slice pilota GRA-A1-001 come richiesto; le altre 97 lezioni non sono state toccate.

### Modifiche effettuate

#### Backend

- **`backend/learning/views.py`**:
  - Fix **P0 sicurezza**: `check_answer` ora filtra `quiz__lezione__ordine_mvp__isnull=False, quiz__lezione__stato_id="PUBBLICATA"`. Non è più possibile ottenere `risposta_corretta` e `spiegazione` di quesiti che appartengono a lezioni in bozza o in preparazione.
  - `path_lessons` include anche le lezioni MVP con `stato_id="DA_SVILUPPARE"` con flag `in_preparazione=True` e `stato="in_preparazione"`. Le lezioni pubblicate mantengono esattamente il comportamento precedente (stati utente disponibile/bloccata/in_corso/completata + prerequisiti mancanti). Estratta la funzione `_lesson_summary_payload`.
  - `lesson_detail` per lezioni non pubblicate restituisce 200 con solo metadati editoriali + `in_preparazione: true` + `stato_utente: "in_preparazione"` + `sezioni: []` + `quiz: []`. Il frontend può quindi mostrare una pagina placeholder invece di un errore.
  - `start_lesson` e `submit_final_quiz` continuano a filtrare solo `stato_id="PUBBLICATA"` (restituiscono 404 su lezioni in preparazione).
- **`backend/fixtures/contenuti_minimi.json`**: rinominata la demo tecnica da `GRA-A1-001`/`VOC-A1-001`/`COM-A1-001` a `DEMO-GRA-001`/`DEMO-VOC-001`/`DEMO-COM-001`. I titoli riportano `[DEMO]` per rimuovere ogni ambiguità con il catalogo editoriale reale. Aggiunta anche la lookup `DA_SVILUPPARE` nella fixture (serve ai test di preparazione).
- **`backend/learning/tests/test_pilot_lesson.py` (nuovo)**: 12 test dedicati alla slice pilota:
  - `IncompleteJsonFragmentTests`: il frammento `sources/GRA-A1-001.json` viene riconosciuto e rifiutato con messaggio esplicito; il comando `importa_contenuti` fallisce e non salva nulla nel DB.
  - `FixtureNamespaceSeparationTests`: nessun ID reale del catalogo compare nella fixture tecnica; tutti gli ID iniziano con `DEMO-` e i titoli con `[DEMO]`.
  - `PathIncludesInPreparationLessonsTests`: una lezione MVP in stato `DA_SVILUPPARE` viene esposta in `/api/percorso/` con flag `in_preparazione` e `stato="in_preparazione"`; `/api/lezioni/<id>/` restituisce placeholder con metadati; `POST /inizia/` e `POST /quiz-finale/` restituiscono 404.
  - `CheckAnswerBlocksUnpublishedTests`: la verifica di un quesito è OK su lezione pubblicata, 404 su lezione in bozza (fix P0 sicurezza).
  - `GuidedExerciseIsNotScoredTests`: l'esercizio guidato esiste come `Quiz.modalita="guidato"` e non aggiorna `Progresso.punteggio` — solo il quiz finale lo fa, e conserva il migliore.
  - `NoAudioNoPRNTests`: la fonte reale (workbook) non contiene campi audio né area PRN.
- **Test esistenti aggiornati**: `test_api.py`, `test_graph.py`, `test_learning.py` ora usano gli ID `DEMO-*` per riflettere la fixture rinominata. Nessuna semantica di test modificata.

#### Frontend

- **`frontend/src/App.jsx`** riscritto per la slice pilota mantenendo l'identità grafica:
  - Componente riutilizzabile `ErrorBox` (❌ → ✅ → perché) esportato, esposto come `<aside>` semantico con `<ul>` per le due righe di confronto e classi separate per accessibilità (`sr-only`, `aria-hidden`).
  - `StatusPill` gestisce il nuovo stato `in_preparazione` con etichetta dedicata.
  - `PathPage`: card in preparazione con badge e nota ("Struttura editoriale definita, contenuti in arrivo"), link con label diverso; `<ul>` semantico e `aria-label` per la lista.
  - `LessonPage`: se `in_preparazione` mostra un `InPreparationLesson` con obiettivo, durata, competenze ed errori tipici tratti dai metadati editoriali, senza sezioni fantasma. Chiama `/inizia/` solo se la lezione è pubblicata.
  - `SectionCarousel` nuovo: **una sezione alla volta** con progress bar accessibile (`role="progressbar"` con `aria-valuenow/min/max`), indicatore "Sezione X di N", puntini di avanzamento, pulsanti Precedente/Successiva e transizione automatica del focus al contenuto della nuova sezione (`tabIndex=-1` + `.focus()`).
  - `QuizView`: banner esplicito per distinguere `guidato` (non fa punteggio) da `finale` (fa punteggio); focus al testo del quesito al cambio; gestione esplicita del caso quiz vuoto ("Quiz in preparazione"); `role="radiogroup"` con `aria-checked` sulle opzioni; `role="progressbar"` sull'indicatore; pulsanti con `type="button"`.
  - Anti-doppio-invio: `busy` flag su verify/finish.
- **`frontend/src/styles.css`** aggiornato:
  - Nuove classi `.status.in_preparazione`, `.lesson-card.in-prep`, `.in-prep-card`, `.in-prep-meta`, `.section-carousel`, `.section-progress`, `.section-nav`, `.section-dots`, `.quiz-banner`, `.sr-only`, `.hero-meta`.
  - Contrasto migliorato su `.requirements` (colore `--warn` più scuro, weight 600) — richiesta review.
  - `@media (max-width: 760px)` copre 390 px: hero più compatto, card lezione a 3 colonne, `section-nav` a wrap con bottoni full-width, `quiz-actions` full-width, `in-prep-meta` a colonna.
  - Rispetto di `prefers-reduced-motion`: transizioni disabilitate.

#### Contenuti

- **Non è stato inventato nulla**. La lezione pilota reale `GRA-A1-001` "L'ordine delle parole: Soggetto + Verbo + Oggetto" resta in stato `Da sviluppare (MVP)` nel workbook; la SPA la mostra come "Contenuto in preparazione" con i metadati editoriali disponibili.

### Problemi corretti in questa passata

- **P0 sicurezza**: `check_answer` esponeva risposte corrette anche su lezioni non pubblicate. Coperto da test dedicato.
- **P0 chiarezza dati**: fixture demo e lezione pilota reale non condividono più lo stesso ID.
- **P0 test mancante**: `_reject_incomplete_json_fragment` ora è coperto da due test (unità + comando).
- **P1 UX**: introdotto lo stato "Contenuto in preparazione" nel percorso e nella pagina lezione.
- **P1 UX**: introdotta la navigazione sezione-per-sezione con indicatore di avanzamento accessibile.
- **P1 A11y**: contrasto della riga "Prima completa", focus management al cambio quesito/sezione, ruoli ARIA corretti su options e progress bar.
- **P1 UX**: banner esplicito nel quiz che distingue guidato (non valutato) da finale (valutato).

### Problemi NON risolti (annotati per iterazioni future)

- **P2** `Progresso.stato` ha default `DISPONIBILE`. Comportamento reale corretto grazie a `sync_progress`, ma il default modello non riflette il DAG.
- **P2** `AUTH_PASSWORD_VALIDATORS = []` e `SECRET_KEY` di sviluppo di default — argomento produzione.
- **P2** `import_content` cancella e ricrea sezioni/quiz a ogni import (atomico, ma non incrementale).

### Assunzioni introdotte

- Fixture tecnica con namespace `DEMO-*` è la convenzione ufficiale per separare contenuti di collaudo dal catalogo editoriale reale. Nessun ID `DEMO-*` verrà mai pubblicato al di fuori dei test.
- Le lezioni MVP con stato `DA_SVILUPPARE` vengono esposte in dashboard come "in preparazione". Non generano `Progresso`, non permettono `/inizia/`, `/quiz-finale/` o `/quesiti/*/verifica/`.
- Lo stato utente `in_preparazione` è distinto dagli stati canonici `bloccata`/`disponibile`/`in_corso`/`completata`. Non entra mai in `Progresso.STATI` — è solo una vista dell'API.

### Contenuti che mi devi fornire per pubblicare davvero GRA-A1-001

Ripeto qui la lista già esposta nella sezione REVIEW CLAUDE — STATO INIZIALE (invariata): 9 blocchi editoriali da sostituire ai `TODO_FONTE`, più i quesiti per esercizio guidato e quiz finale. Fino a che non arrivano, la lezione resta "in preparazione".

### Verifiche eseguite (baseline finale)

- `../.venv/bin/python manage.py test -v 2` → **39/39 verdi** (26 preesistenti + 13 nuovi dedicati alla slice pilota).
- `../.venv/bin/python manage.py check` → **0 problemi**.
- `../.venv/bin/python manage.py makemigrations --check --dry-run` → **nessuna modifica al modello**.
- `../.venv/bin/python manage.py valida_contenuti ../programma_lezioni_inglese_no_audio.xlsx --json` → **valido** (98 lezioni, 29 MVP, 119 prerequisiti, 824 sezioni TODO, 0 quiz).
- `pnpm build` → **non eseguibile in questa macchina** (Node/pnpm/npm non installati). Va lanciato da te dopo aver ripristinato l'ambiente Node. Il codice frontend non è stato collaudato nel browser in questa passata: elenco sotto cosa collaudare a mano appena hai Node.

### Collaudo browser da fare a mano (non ho Node in questo ambiente)

1. `cd frontend && pnpm install && pnpm build` — deve completare senza errori.
2. `pnpm dev` + backend up (`cd backend && ../.venv/bin/python manage.py importa_contenuti ../programma_lezioni_inglese_no_audio.xlsx && ../.venv/bin/python manage.py runserver`).
3. Aprire `http://localhost:5173`, registrarsi, visitare `/percorso`. Deve elencare **29 card "In preparazione"** ordinate per MVP + eventuali `DEMO-*` se importi la fixture invece del workbook. La lezione pilota `GRA-A1-001` appare in cima con badge "In preparazione".
4. Aprire la card `GRA-A1-001`: deve mostrare la pagina placeholder con obiettivo, durata, competenze, errori tipici e nessuna sezione.
5. Importare invece la fixture (`../.venv/bin/python manage.py importa_contenuti fixtures/contenuti_minimi.json`) per collaudare il motore su `DEMO-GRA-001`: navigazione sezione-per-sezione con progress bar, esercizio guidato senza punteggio, quiz finale 8 quesiti con soglia 70%, feedback immediato.
6. Ridurre finestra a 390 px: card lezione a 3 colonne senza troncamenti; hero compatto; navigazione sezioni con bottoni full-width; quiz leggibile.
7. Con la tastiera: Tab attraversa nav → card → apri lezione → sezioni; il focus arriva al nuovo `<h2>` a ogni sezione e al `<h3>` a ogni quesito. Skip link visibile al primo Tab.

### Prossimi passi consigliati (in ordine di priorità)

1. **Fornire i contenuti definitivi di GRA-A1-001** (9 blocchi + esercizi + quiz) così da poterla pubblicare davvero.
2. Ripetere la stessa slice per una seconda lezione (`GRA-A1-002` o `VOC-A1-001`) applicando lo stesso pattern.
3. Solo dopo, decidere la strategia per le due radici MVP (`GRA-A1-001` e `VOC-A1-001`) prima di pubblicare l'intero percorso.

## STATO ATTUALE

Rilevazione iniziale eseguita prima delle modifiche e aggiornata al termine del giro del 2026-07-20.

### Implementato e funzionante, file per file

- `backend/learning/models.py`: utente email/password, lookup relazionali, lezioni, prerequisiti molti-a-molti, sezioni, quiz/quesiti esclusivamente testuali e progressi univoci per `(utente, lezione)`; `priorita` P0–P3, aree GRA/VOC/COM e `ordine_percorso` 1–98 sono vincolati. Non esistono campi o entità audio.
- `backend/learning/importer.py`: caricamento JSON, Excel normalizzato e workbook editoriale; import atomico e idempotente; lookup alimentate dalla fonte; catalogo da 98 lezioni, MVP da 29, priorità, divieto di campi audio, conteggio sezioni per area e DAG validati prima di ogni scrittura.
- `backend/learning/services.py`: controlli rumorosi per ID inesistenti, prerequisiti fuori MVP, ordine non valido, cicli, nodo iniziale e raggiungibilità; sblocco basato su tutti i prerequisiti; soglia quiz 70%, completamento e miglior punteggio.
- `backend/learning/views.py`, `serializers.py`, `urls.py`: API DRF per registrazione/login, profilo, percorso, dettaglio lezione, avvio, verifica immediata dei quesiti, invio quiz finale, progressi e controllo editoriale staff.
- `backend/learning/management/commands/importa_contenuti.py` e `valida_contenuti.py`: import reale o `--dry-run` e report testuale/JSON adatto alla CI.
- `backend/learning/admin.py`: gestione editoriale di lezioni, prerequisiti, sezioni, quiz, progressi, utenti e lookup.
- `backend/fixtures/contenuti_minimi.json`: fixture tecnica di tre lezioni pubblicate nelle sole aree GRA/VOC/COM, priorità P0, sezioni 9/7/8 e dimostrazione testuale dei due tipi di quesito, esercizio guidato e quiz finale da 8 domande.
- `backend/learning/tests/`: 26 test su import idempotente, DAG, raggiungibilità persistita, sblocco, priorità, esclusione PRN/audio, miglior punteggio, API, autorizzazioni staff, comandi, workbook reale e percorso utente end-to-end.
- `frontend/src/App.jsx`: SPA con `/percorso`, `/lezioni/<id>`, `/progressi`, `/profilo`, `/login`, `/registrati` e pagina staff; mostra i prerequisiti mancanti; include il box riutilizzabile `❌ → ✅ → perché` e il motore quiz testuale.
- `frontend/src/api.js` e `styles.css`: client autenticato, gestione errori, UI italiana responsive e accessibile; collaudata nel browser desktop e a 390 px.
- `README.md`, `.env.example`, `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` e `.github/workflows/ci.yml`: istruzioni locali, configurazione SQLite/PostgreSQL, container e pipeline di check/test/build/validazione contenuti.

### Incompleto o abbozzato

- Il workbook locale contiene materialmente ancora 28 righe nel foglio `Percorso MVP`; il parser applica e segnala la normalizzazione richiesta a 29 finché non arriva la fonte aggiornata.
- Il workbook editoriale contiene 824 sezioni pianificate ma nessun testo definitivo e nessun quesito importabile: il parser conserva `TODO_FONTE` e non inventa contenuti o quiz.
- Tutte le lezioni MVP del workbook hanno stato `DA_SVILUPPARE`; il percorso reale non è ancora pubblicabile. La fixture tecnica è l'unica fonte eseguibile con contenuti e quiz dimostrativi.
- Il workbook ha due radici MVP (`GRA-A1-001`, `VOC-A1-001`); non viola ancora la raggiungibilità delle lezioni pubblicate perché nel workbook nessuna lezione è pubblicata, ma resta una decisione editoriale aperta.
- Docker Compose è configurato ma non è stato eseguito nell'ambiente locale perché Docker non è installato.

### ASSUNZIONI in vigore

- Autenticazione predefinita email + password, minimo 8 caratteri, con token DRF.
- Quiz finale superato al 70%, ripetibile senza limiti; viene conservato il punteggio migliore.
- Il DAG, non l'importanza editoriale, decide lo sblocco; lezioni Consigliate e Secondarie non vengono saltate automaticamente.
- `Quiz.modalita` distingue esercizio `guidato` non valutato e quiz `finale` valutato.
- Nei completamenti si ignorano spazi esterni e maiuscole/minuscole; la scelta multipla richiede corrispondenza esatta.
- `competenze` ed `errori_tipici` sono array JSON; i contenuti strutturati delle sezioni sono oggetti JSON.
- Il nodo iniziale è la lezione pubblicata con `ordine_mvp` più basso; una lezione entra nella navigazione MVP solo con `ordine_mvp` valorizzato e stato `PUBBLICATA`.
- La fixture è tecnica e temporanea; non è fonte editoriale e va sostituita dal JSON reale.
- **ASSUNZIONE nuova:** poiché il workbook locale non assegna ancora un'importanza a `GRA-A1-008`, viene inserita all'ordine MVP 11 come `Consigliata`/P1, coerentemente con la lezione successiva `GRA-A1-009`; tutti gli ordini successivi slittano di uno.
- P0/P1/P2 corrispondono rigidamente a Essenziale/Consigliata/Secondaria; P3 è riservata alle lezioni post-MVP.

### Verifica corrente

- `python manage.py test -v 2`: **26/26 test passati**.
- `PersistedPublishedGraphBuildTest`: **passato**; tutte le lezioni pubblicate della fixture sono raggiungibili dal nodo iniziale.
- Test espliciti per ciclo, ID inesistente, prerequisito fuori MVP, prerequisito verso ordine superiore e lezione non raggiungibile: **passati** perché ciascuna anomalia fa fallire rumorosamente la validazione.
- `python manage.py makemigrations --check --dry-run`: **passato**, nessuna modifica rilevata.
- Build Vite di produzione: **passata**.
- Validazione e dry-run del workbook locale: **passati**, 98 lezioni, 29 MVP, 119 prerequisiti, nessun errore DAG.

## 0.4.0 — 2026-07-20

### Aggiornamento perimetro e modello

- Aggiunto `Lezione.priorita` con valori P0–P3, esposto nelle API, nella dashboard e nel controllo editoriale staff.
- Aggiunti vincoli applicativi e database: sole aree GRA/VOC/COM e `ordine_percorso` compreso tra 1 e 98.
- Aggiunta migrazione dati che elimina eventuali lezioni/lookup PRN legacy e assegna la priorità agli eventuali record esistenti in base a `importanza_mvp`.
- Rimossi PRN dalla fixture, dal frontend, dagli stili e dai conteggi delle sezioni.
- Confermata l'assenza di modelli, campi o componenti audio; l'importatore ora respinge esplicitamente qualsiasi campo sorgente contenente `audio` nel nome.

### Import e DAG

- Il parser del workbook locale normalizza il vecchio foglio da 28 righe: inserisce `GRA-A1-008` all'ordine MVP 11 e porta il percorso a 29 lezioni.
- Aggiunte validazioni per catalogo da 98 lezioni, ordini continui 1–98 e 1–29, priorità coerente con `importanza_mvp`, sole tre aree e divieto audio.
- Il workbook reale è ora valido: `GRA-A1-009` dipende da `GRA-A1-008` dentro il perimetro MVP.
- La raggiungibilità delle lezioni pubblicate non può più attraversare lezioni non pubblicate.
- Gli endpoint di avvio lezione e quiz finale rifiutano lezioni non pubblicate.
- La navigazione utente resta esplicitamente ordinata per `ordine_mvp`; `priorita` ordina il lavoro editoriale nell'admin e nella pagina staff.

### Test e verifica

- Aggiornato il test del workbook: 98 lezioni, 29 MVP, `GRA-A1-008` in posizione 11, `GRA-A1-009` in posizione 12 e validazione DAG positiva.
- Aggiunti test per PRN, campi audio, coerenza priorità/importanza, persistenza priorità e cammini che attraversano lezioni non pubblicate.
- Suite portata a 26 test tutti verdi, incluso l'import reale ripetuto delle 98 lezioni; check Django, controllo migrazioni, dry-run del workbook e build React passano.
- Aggiornata la CI: la validazione del workbook deve ora essere verde.

### ASSUNZIONI

- `GRA-A1-008` è `Consigliata`/P1 finché la fonte ufficiale aggiornata non dichiara esplicitamente la sua importanza.
- La normalizzazione è applicata soltanto al workbook editoriale legacy quando `GRA-A1-008` manca e `GRA-A1-009` è presente; il futuro JSON reale deve già contenere tutte le 29 lezioni MVP.

### Domande aperte / TODO FONTE

- Fornire il JSON reale aggiornato delle 98 lezioni con `priorita`, `importanza_mvp` e 29 valori di `ordine_mvp`.
- Fornire i testi definitivi delle 824 sezioni e i quesiti; il workbook attuale non contiene quiz importabili.
- Confermare o sostituire l'ASSUNZIONE `GRA-A1-008 = Consigliata/P1` nella fonte ufficiale.
- Chiarire se le due radici MVP (`GRA-A1-001`, `VOC-A1-001`) debbano essere collegate prima della pubblicazione; non è stato inventato alcun prerequisito.
- L'ispezione visuale del file Excel tramite la libreria del runtime è stata impedita da una firma nativa macOS non compatibile; struttura e dati sono stati verificati attraverso lo stesso parser usato dall'app e dai test.

## 0.3.1 — 2026-07-20

### Correzioni dal collaudo visuale

- Corretto l'accesso API quando la SPA locale viene aperta da `127.0.0.1` anziché `localhost`.
- L'URL API di sviluppo ora usa automaticamente lo stesso hostname della pagina.
- Le origini CORS locali predefinite includono sia `localhost:5173` sia `127.0.0.1:5173`.
- Le sezioni che contengono solo un esempio non generano più paragrafi HTML vuoti.
- Separata correttamente la navigazione “Percorso” dai metadati nell'intestazione della lezione.
- Collaudati nel browser i flussi di registrazione, sblocco, lezione, esercizio guidato, quiz finale, progressi e profilo, anche a 390 px di larghezza.

## 0.3.0 — 2026-07-19

### Hardening tecnico

- Il validatore DAG ora raccoglie tutte le anomalie rilevabili in un'unica esecuzione.
- Aggiunto `importa_contenuti --dry-run`, che valida senza scrivere nel database.
- Aggiunto `valida_contenuti`, con output umano o JSON per CI.
- Il report reale include conteggi, radici MVP, prerequisiti fuori perimetro, stato di pubblicazione, sezioni TODO e quiz mancanti.
- Aggiunto Docker Compose con backend Django/Gunicorn, frontend React/Nginx e PostgreSQL 17.
- Aggiunta workflow CI per test backend, controllo migrazioni, build frontend e validazione del workbook.
- Aggiunto test end-to-end: registrazione → percorso → lezione → quiz → completamento → sblocco.
- Portata la suite a 19 test automatici.
- Migliorato Django Admin con filtri, ricerca e inline per prerequisiti, sezioni e quiz.
- Aggiunta API riservata allo staff e pagina `/contenuti-da-completare` per il controllo editoriale.
- Migliorata l'accessibilità con skip link, focus visibile, regioni live e navigazione etichettata.

### NOTA OPERATIVA

- La CI dei test e della build è verde; lo step di validazione della fonte resta intenzionalmente rosso per `GRA-A1-009 → GRA-A1-008` fuori dal perimetro MVP.
- La configurazione Docker è stata aggiunta ma non eseguita in locale perché Docker non è installato nell'ambiente di sviluppo corrente.

## 0.2.0 — 2026-07-19

### Integrazione del workbook reale

- Ispezionato integralmente `programma_lezioni_inglese_no_audio.xlsx`: 8 fogli, 98 lezioni, 28 righe MVP e 3 template di area.
- Aggiunto il parser nativo dei fogli `Programma Lezioni`, `Percorso MVP`, `Grammatica`, `Vocabolario`, `Comunicazione` e `Liste`.
- Mappate dal file tutte le lookup, le lezioni, le dipendenze, le competenze, gli errori tipici, `ordine_mvp` e `importanza_mvp`.
- Generati 824 record di sezione esclusivamente dai template sorgente. Il testo pianificato è marcato `TODO_FONTE`, non presentato come contenuto didattico finito.
- Nessun quiz è stato generato: il workbook descrive la struttura dei quiz ma non contiene quesiti, opzioni, risposte corrette o spiegazioni.
- Aggiunto un controllo esplicito sui prerequisiti di lezioni MVP che puntano a lezioni fuori dal `Percorso MVP`.
- Aggiunti test di regressione sul formato reale e sull'incoerenza rilevata.

### BLOCCO RILEVATO NELLA FONTE

- `GRA-A1-009` (ordine MVP 11) richiede `GRA-A1-008`, ma `GRA-A1-008` non compare nel foglio `Percorso MVP`. L'import fallisce intenzionalmente con `Prerequisito fuori perimetro MVP`.
- Il percorso MVP contiene due nodi senza prerequisiti (`GRA-A1-001` e `VOC-A1-001`). Se entrambi venissero pubblicati così, `VOC-A1-001` e il suo ramo non sarebbero raggiungibili dal nodo iniziale unico.
- Tutte le 28 lezioni MVP hanno stato sorgente `Da sviluppare (MVP)`; nessuna è `Pubblicata`. Il parser preserva questo stato e non pubblica contenuti automaticamente.

### TODO FONTE

- Correggere nel workbook il perimetro o il prerequisito di `GRA-A1-009`.
- Chiarire/collegare il secondo nodo iniziale `VOC-A1-001` per ottenere un unico grafo raggiungibile.
- Fornire testi definitivi per ogni sezione e 8–10 quesiti misti per ogni quiz finale.
- Confermare se il livello `C2`, presente in `Liste` ma non nel modello richiesto A1–C1, debba restare come lookup futura.

## 0.1.0 — 2026-07-19

### Costruito

- Repository eseguibile con backend Django/DRF e SPA React/Vite.
- Modello dati relazionale completo: lookup, lezioni, DAG dei prerequisiti, sezioni, quiz/quesiti, utenti e progressi.
- Autenticazione email/password tramite token DRF; pagine `/login`, `/registrati`, `/profilo`.
- Import atomico e idempotente da JSON o Excel, incluse le lookup del foglio `Liste`.
- Validazione rumorosa di ID inesistenti/fuori perimetro, ordine dei prerequisiti, cicli, nodo iniziale e raggiungibilità delle lezioni pubblicate.
- Fixture temporanea con tre lezioni A1 e un set dimostrativo di esercizio guidato + quiz finale testuale.
- Stati persistiti per `(utente, lezione)` e ricalcolati dal DAG: bloccata, disponibile, in corso, completata.
- Soglia, ripetizione, miglior punteggio, minuti effettivi e timestamp di completamento.
- Dashboard `/percorso` ordinata per `ordine_mvp`, con nomi dei prerequisiti mancanti.
- Rendering `/lezioni/<id>` con identità visiva per area, feedback immediato e componente riutilizzabile `❌ → ✅ → perché`.
- Pagine `/progressi` e `/profilo`, UI responsive in italiano e nessuna dipendenza runtime da servizi esterni.
- Test automatici per DAG/raggiungibilità, import, sblocco, miglior punteggio e API di scoring.

### ASSUNZIONI

- L'autenticazione predefinita è email + password; la password minima è di 8 caratteri e il client usa token DRF.
- La soglia del quiz finale è 70%; i tentativi sono illimitati e resta il punteggio migliore.
- Lezioni Consigliate e Secondarie non si saltano: decide unicamente il DAG dei prerequisiti.
- È stato aggiunto `Quiz.modalita` (`guidato` oppure `finale`) per distinguere l'esercizio non valutato dal quiz che aggiorna il progresso.
- Il confronto dei completamenti ignora maiuscole/minuscole e spazi esterni; la scelta multipla richiede corrispondenza esatta.
- `errori_tipici` è memorizzato come array JSON, coerentemente con `competenze`, per supportare più errori e il box riutilizzabile.
- La lezione pubblicata con `ordine_mvp` più basso è il nodo iniziale e non può avere prerequisiti.
- Le lezioni mostrate nell'MVP devono avere stato lookup `PUBBLICATA` e `ordine_mvp` valorizzato.
- La fixture è esclusivamente tecnica e temporanea: i suoi contenuti dimostrativi vanno sostituiti integralmente dal file sorgente reale.
- Le strutture dei fogli Excel sono quelle documentate nel README, non essendo disponibile il file reale.

### Domande aperte / TODO

- **TODO fonte contenuti:** sostituire la fixture con il file Excel/JSON ufficiale, fonte di verità, senza conservare testi o quiz dimostrativi.
- Confermare nomi esatti dei fogli, intestazioni, codici e valori del foglio `Liste`; adattare soltanto il parser se differiscono.
- Confermare se tutte le lezioni debbano avere entrambi i quiz. La fixture dimostra il motore sulla prima lezione; sulle altre non inventa quesiti aggiuntivi.
- Confermare i tipi e i formati web ufficiali delle sezioni per ciascuna area.
- Definire policy di password, recupero password e verifica email per la produzione.
- Definire modalità di conteggio di `minuti_effettivi`; l'API accetta per ora i minuti dichiarati dal client.
