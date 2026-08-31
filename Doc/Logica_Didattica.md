# Logica didattica e roadmap di prodotto

> **Provenienza.** Questo documento conserva il contenuto dei fogli `Logica Didattica` e
> `Roadmap` di `programma_lezioni_inglese_no_audio.xlsx`, rimossi dal workbook il 31/08/2026
> perché nessuna parte del codice li leggeva. Il testo è riportato **integralmente e alla
> lettera**: è il ragionamento che ha prodotto la struttura del programma, e non esisteva
> altrove nel repository.
>
> Alcune affermazioni descrivono il progetto com'era pensato all'origine e **non
> corrispondono più all'implementazione attuale**. Non sono state corrette nel testo, per non
> falsificare un documento storico: le differenze sono elencate nella
> [Nota di allineamento](#nota-di-allineamento) in fondo.

---

## LOGICA DIDATTICA

*Le scelte progettuali alla base della nuova struttura del programma.*

### 1. Categorie scelte

Tre aree didattiche: GRAMMATICA (il sistema della lingua), VOCABOLARIO (le parole e le combinazioni) e COMUNICAZIONE (l'uso reale della lingua). Ogni area ha un codice ID (GRA, VOC, COM), un colore e un template di pagina dedicato.

### 2. Perché Dialogo e Produzione sono state unite

Le vecchie categorie Dialogo e Produzione si sovrapponevano: entrambe allenavano la produzione orale e la differenza (conversazione a due vs. monologo/testo) è una differenza di FORMATO dell'attività, non di area didattica. Sono state quindi unite nell'area COMUNICAZIONE, e la distinzione è diventata una «Tipologia Lezione» interna con tre valori: DIALOGO (comprensione + interazione guidata in uno scenario), PRODUZIONE GUIDATA (lo studente produce con modello e traccia) e PRODUZIONE LIBERA (lo studente produce in autonomia con feedback). Questo realizza la distinzione didatticamente corretta comprensione → produzione guidata → produzione libera, senza moltiplicare le sezioni della Web App: nel menu l'utente vede una sola area «Comunicazione».

### 3. Categorie eliminate o reintegrate

Speaking e Scrittura NON tornano come categorie separate: sono competenze trasversali, tracciate nella colonna «Competenze Allenate» (ogni lezione di Comunicazione indica se allena speaking, scrittura o entrambi).

### 4. Progressione da A1 a C1

Ogni livello CEFR è un «capitolo» del percorso. Dentro ogni livello le lezioni si alternano secondo il ciclo: strumenti (grammatica + lessico) → applicazione (dialogo) → produzione guidata → produzione libera. La colonna «Ordine nel Percorso» definisce la sequenza consigliata unica (1-104); «Lezione Precedente/Successiva» la rendono navigabile; «Prerequisiti» elenca le dipendenze reali (che possono attraversare le aree: es. il dialogo «Raccontare il weekend» richiede il past simple). La difficoltà è ricalibrata ALL'INTERNO di ogni livello (una lezione A1 «Alta» resta più facile di una B2 «Bassa»).

### 5. Collegamento tra grammatica, vocabolario e comunicazione

Regola dei blocchi: prima si insegnano gli strumenti (GRA/VOC), poi si usano in uno scenario (COM-Dialogo), poi si produce (COM-Produzione). Esempio A1: to be → «Presentarsi e salutare» (dialogo) → «Parlare di sé» (produzione guidata). Ogni lezione COM dichiara nei prerequisiti le lezioni GRA/VOC necessarie, così la Web App può bloccare o consigliare le lezioni nell'ordine giusto con una semplice logica a dipendenze.

### 6. Come si evitano le sovrapposizioni

Speaking, Scrittura, Dialogo e Produzione non sono più categorie parallele ma tre livelli distinti del modello dati: AREA (dove sta la lezione nel menu) → TIPOLOGIA (che formato ha l'attività) → COMPETENZE (cosa allena). Una lezione appartiene a una sola area e a una sola tipologia, ma può allenare più competenze. Questo elimina ogni ambiguità di classificazione.

### 7. Focus sugli studenti italiani

Ogni lezione ha la colonna «Errori Tipici degli Italiani» con calchi, falsi amici e interferenze specifiche (I have 25 years, informations, I am agree, in Monday, listen music...). Sono state aggiunte lezioni che esistono SOLO in ottica italiana: falsi amici (A1 e B1), preposizioni in/on/at, articoli avanzati e omissione, verbi+preposizioni.

### 8. Correzioni principali rispetto alla bozza

a) Aggiunto il PRESENT CONTINUOUS, assente nella bozza pur essendo obbligatorio in A1, con lezione di contrasto simple/continuous. b) Aggiunte 8 lezioni A1 mancanti (possessivi, dimostrativi, question words, can, preposizioni, avverbi di frequenza...). c) Il Vocabolario passa da 3 a 17 lezioni: era sottodimensionato rispetto al suo peso didattico. d) Aggiunta la negativa/interrogativa del past simple (mancava). e) Riequilibrate le difficoltà (es. «to be negativa» da Media a Bassa; «present simple vs continuous» ad Alta). f) Aggiunti scenari comunicativi mancanti (negozio, reclami, e-mail semplice in A2). g) Descrizioni differenziate per tipologia invece del testo fotocopia.

### 9. Struttura minima per l'MVP

MVP = solo livello A1 con le 3 aree già presenti ma in versione ridotta: ~26 lezioni (vedi foglio «Percorso MVP»). Funzionalità minime: pagina-lezione secondo i template, quiz a scelta multipla/completamento, percorso lineare con blocco sui prerequisiti, salvataggio dei progressi. Rimandate a fasi successive: feedback automatico sulla produzione libera, spaced repetition del lessico.

---

## ROADMAP DI SVILUPPO

*Cinque fasi incrementali: ogni fase produce una app utilizzabile e più completa della precedente.*

### Fase 1 — MVP

| Campo | Valore |
| --- | --- |
| Obiettivo | Percorso A1 completo e utilizzabile «da zero alla prima conversazione». |
| Lezioni da sviluppare | Le 26 lezioni del foglio «Percorso MVP» (partendo dalle 12 Essenziali). |
| Categorie coinvolte | Grammatica, Vocabolario, Comunicazione |
| Funzionalità necessarie | Pagina-lezione secondo i 3 template; quiz a scelta multipla e completamento; percorso lineare con blocco sui prerequisiti; salvataggio progressi. |
| Priorità | Alta |
| Complessità | Media |
| Dipendenze | Nessuna |

### Fase 2 — Ampliamento A1-A2

| Campo | Valore |
| --- | --- |
| Obiettivo | Coprire integralmente i livelli A1 e A2 (56 lezioni totali). |
| Lezioni da sviluppare | Le lezioni A1 rimanenti (Secondarie) e tutte le 25 lezioni A2. |
| Categorie coinvolte | Tutte e tre le aree |
| Funzionalità necessarie | Esercizi di riordino frase e abbinamento; dettati brevi; ripasso programmato del lessico (spaced repetition); statistiche di avanzamento per area. |
| Priorità | Alta |
| Complessità | Media |
| Dipendenze | Fase 1 completata |

### Fase 3 — Introduzione B1

| Campo | Valore |
| --- | --- |
| Obiettivo | Aprire il livello intermedio con test d'ingresso. |
| Lezioni da sviluppare | Le 22 lezioni B1 (priorità: present perfect vs past simple, tempi narrativi, phrasal verbs, colloquio di lavoro). |
| Categorie coinvolte | Tutte e tre le aree |
| Funzionalità necessarie | Test di livello iniziale; produzione scritta con auto-valutazione guidata (checklist); registrazione vocale per lo speaking; certificato di completamento livello. |
| Priorità | Media |
| Complessità | Alta |
| Dipendenze | Fase 2 completata |

### Fase 4 — Ampliamento B2-C1

| Campo | Valore |
| --- | --- |
| Obiettivo | Completare il percorso fino al livello avanzato. |
| Lezioni da sviluppare | Le 15 lezioni B2 e le 11 lezioni C1. |
| Categorie coinvolte | Grammatica, Vocabolario, Comunicazione |
| Funzionalità necessarie | Feedback AI sulla produzione libera (scritta e orale); simulazioni di dialogo a risposta aperta; percorsi tematici (Business English, Travel). |
| Priorità | Media |
| Complessità | Alta |
| Dipendenze | Fase 3 completata |

### Fase 5 — Funzionalità avanzate

| Campo | Valore |
| --- | --- |
| Obiettivo | Fidelizzazione e personalizzazione dell'apprendimento. |
| Lezioni da sviluppare | Nessuna nuova lezione: consolidamento e contenuti extra (lezioni stagionali, cultura). |
| Categorie coinvolte | Trasversale |
| Funzionalità necessarie | Percorsi adattivi basati sugli errori dell'utente; gamification (streak, badge, classifiche); modalità ripasso rapido; app offline; notifiche intelligenti. |
| Priorità | Bassa |
| Complessità | Alta |
| Dipendenze | Fasi 1-4; base utenti attiva |

---

## Nota di allineamento

Punti in cui il testo qui sopra **non descrive più il progetto attuale**.

| Il documento dice | Stato attuale | Dove verificarlo |
| --- | --- | --- |
| «Ordine nel Percorso» va da **1-104** | Il catalogo è di **98 lezioni**, e l'ordine deve essere una permutazione esatta di 1..98 | `CATALOG_LESSON_COUNT` in [importer.py](../backend/learning/importer.py); vincolo `ordine_percorso_1_98` in [models.py](../backend/learning/models.py) |
| MVP di **~26 lezioni**, «partendo dalle 12 Essenziali» | MVP di **29 lezioni**. La classificazione Essenziale/Consigliata/Secondaria è stata eliminata insieme alla tabella `learning_importanza` | `MVP_LESSON_COUNT` in [importer.py](../backend/learning/importer.py) |
| «percorso lineare con **blocco sui prerequisiti**»; «la Web App può bloccare le lezioni» | **Nessuna lezione è mai bloccata.** I 119 archi prerequisito sono stati rimossi con la migration `0008`: l'ordine è un suggerimento (`ordine_mvp`, `ordine_percorso`), non un cancello | `lesson_state()` in [services.py](../backend/learning/services.py); nota `NOTA_PREREQUISITI` in [aggiorna_workbook.py](../backend/scripts/aggiorna_workbook.py) |
| Le colonne «Prerequisiti», «Lezione Precedente/Successiva» rendono il percorso navigabile | Le tre colonne **esistono ancora nel foglio** `Programma Lezioni` ma **l'importer non le legge**: non arrivano né al database né al sito | ciclo lezioni in [importer.py](../backend/learning/importer.py) |
| Ogni area ha «un template di pagina dedicato» | Vero, ed è ancora così: fogli `Grammatica` (9 sezioni), `Vocabolario` (7), `Comunicazione` (8) | `AREA_SECTION_COUNTS` in [importer.py](../backend/learning/importer.py) |
| Le tipologie DIALOGO / PRODUZIONE GUIDATA / PRODUZIONE LIBERA | Ancora presenti come valori di `Tipologia Lezione` nel foglio `Liste` | foglio `Liste`, colonna B |

Il resto del ragionamento — le tre aree, l'unione di Dialogo e Produzione, le competenze come dimensione trasversale, il focus sugli errori tipici degli italiani — descrive fedelmente il progetto attuale.
