# Changelog

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
