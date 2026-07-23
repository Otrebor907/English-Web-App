# Prompt master per Claude Code

Copia il prompt seguente in Claude Code quando vuoi trasformare uno o più brief in pagine dell'app.

```text
Leggi prima il file lezioni_markdown/_schema.md e poi il brief Markdown della lezione che ti indicherò.

Trasforma il brief in una pagina completa dell'app, con contenuto didattico ed esercizi realmente compilati. Il Markdown è la fonte editoriale autorevole; il codice esistente è la fonte autorevole per componenti, route, persistenza dei progressi e stile.

Prima di modificare:
1. analizza le route e i componenti delle lezioni esistenti;
2. indicami i file che vuoi creare o modificare;
3. riassumi la struttura della pagina e il modello dati degli esercizi;
4. non eliminare file senza autorizzazione.

Durante l'implementazione:
- conserva l'accesso libero a tutte le lezioni;
- usa i prerequisiti soltanto come suggerimenti;
- mantieni i progressi esistenti;
- presenta teoria ed esempi a scorrimento continuo;
- colloca esercizio, invio, correzione e possibilità di riprovare in fondo;
- inserisci tutte le domande, risposte, spiegazioni e varianti richieste dal brief;
- non aggiungere audio;
- non inventare nuove lezioni o cambiare ID, livello e ordine;
- riutilizza design system e componenti del progetto.

Dopo l'implementazione esegui test, lint e build disponibili, quindi controlla manualmente la pagina a 320, 375, 414, 768 px e desktop.

Brief da implementare:
<INCOLLA QUI IL PERCORSO DEL FILE .md>
```
