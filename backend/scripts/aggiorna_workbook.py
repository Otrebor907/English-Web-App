"""Allinea un workbook del programma allo schema Neon dopo la migration 0006.

Uso: python3 aggiorna_workbook.py <file.xlsx> [altro.xlsx ...]

Idempotente: rieseguirlo su un file gia' aggiornato non cambia nulla.
"""
import sys
import warnings

warnings.filterwarnings("ignore")

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

TITLE = Font(name="Arial", size=14, bold=True)
SUB = Font(name="Arial", size=10, italic=True, color="595959")
HEAD = Font(name="Arial", size=10, bold=True, color="FFFFFF")
BODY = Font(name="Arial", size=10)
FILL = PatternFill("solid", fgColor="1F4E5F")
WRAP = Alignment(wrap_text=True, vertical="top")

COLS = ["Colonna", "Tipo Neon", "Obbligatoria", "Descrizione"]
WIDTHS = [26, 22, 14, 68]

QUESITO = [
    ("id", "bigint (identity)", "si", "Chiave primaria tecnica. Univoca solo dentro questa tabella."),
    ("quiz_id", "bigint FK", "si", "Riferimento a struttura_quiz.id, modalita {modalita}."),
    ("ordine", "smallint", "si", "Posizione del quesito. UNIQUE con quiz_id."),
    ("tipo", "varchar(20)", "si", "completamento oppure scelta_multipla."),
    ("testo", "text", "si", "Testo del quesito mostrato all'utente."),
    ("opzioni", "jsonb", "si", "Alternative per scelta_multipla; lista vuota per completamento."),
    ("risposta_corretta", "varchar(300)", "si", "Soluzione. Varianti accettate separate da «|»."),
    ("spiegazione", "text", "si", "Mostrata dopo la verifica. Mai inviata al client prima della risposta."),
]

SHEETS = {
    "Struttura_Lezione": (
        "STRUTTURA_LEZIONE — sezioni che compongono una lezione",
        "Tabella Neon: struttura_lezione (ex learning_sezionelezione). Una riga per sezione, "
        "ordinata da «ordine» (UNIQUE con lezione_id). I template per area sono nei fogli Grammatica / Vocabolario / Comunicazione.",
        [
            ("id", "bigint (identity)", "si", "Chiave primaria tecnica."),
            ("lezione_id", "varchar(32) FK", "si", "Riferimento a learning_lezione.id."),
            ("ordine", "smallint", "si", "Posizione della sezione. UNIQUE con lezione_id."),
            ("tipo_sezione", "varchar(80)", "si", "Nome della sezione, es. «Regola e uso»."),
            ("contenuto", "jsonb", "si", "Chiavi tipiche: titolo, testo, elementi. Con formato_web = todo contiene il segnaposto TODO_FONTE."),
            ("formato_web", "varchar(40)", "si", "Resa nel frontend: testo, lista, errore_box, todo."),
        ],
    ),
    "Struttura_Quiz": (
        "STRUTTURA_QUIZ — parte esercitativa della lezione",
        "Tabella Neon: struttura_quiz (ex learning_quiz). Al massimo due righe per lezione, una per modalita. "
        "I quesiti stanno nei fogli struttura_quiz_guidato e struttura_quiz_finale.",
        [
            ("id", "bigint (identity)", "si", "Chiave primaria tecnica."),
            ("lezione_id", "varchar(32) FK", "si", "Riferimento a learning_lezione.id."),
            ("modalita", "varchar(10)", "si", "guidato oppure finale. UNIQUE con lezione_id."),
            ("titolo", "varchar(160)", "si", "Titolo mostrato all'utente."),
        ],
    ),
    "struttura_quiz_guidato": (
        "STRUTTURA_QUIZ_GUIDATO — quesiti dell'esercizio guidato",
        "Tabella Neon: struttura_quiz_guidato, dalla separazione di learning_quesito. Correzione immediata, "
        "un quesito alla volta, senza punteggio. API: /api/lezioni/<id>/quiz/guidato/quesiti/<qid>/verifica/",
        [(a, b, c, d.format(modalita="guidato")) for a, b, c, d in QUESITO],
    ),
    "struttura_quiz_finale": (
        "STRUTTURA_QUIZ_FINALE — quesiti del quiz finale",
        "Tabella Neon: struttura_quiz_finale, dalla separazione di learning_quesito. Corretti in blocco: "
        "producono il punteggio in learning_progresso (soglia 70). API: /api/lezioni/<id>/quiz/finale/quesiti/<qid>/verifica/",
        [(a, b, c, d.format(modalita="finale")) for a, b, c, d in QUESITO],
    ),
}

MODELLO_DATI = [
    ("mapping_area_lezione", "learning_area", "Liste (col. Area Didattica)", "Rinominata: tabella di mapping codice→etichetta."),
    ("mapping_tipologia", "learning_tipologia", "Liste (col. Tipologia Lezione)", "Rinominata."),
    ("mapping_livello", "learning_livello", "Liste (col. Livello Linguistico)", "Rinominata."),
    ("mapping_difficolta_lezione", "learning_difficolta", "Liste (col. Difficoltà)", "Rinominata, senza accento: un identificatore accentato andrebbe virgolettato in ogni query Postgres."),
    ("learning_statolezione", "—", "Liste (col. Stato della Lezione)", "Invariata: fuori dal perimetro del refactor."),
    ("learning_lezione", "—", "Programma Lezioni", "Rimosse le colonne priorita e importanza_mvp_id."),
    ("learning_prerequisito", "—", "Programma Lezioni (Prerequisiti) e Percorso MVP (Dipendenze)", "MANTENUTA: vedi nota in fondo."),
    ("struttura_lezione", "learning_sezionelezione", "Struttura_Lezione", "Rinominata: è la struttura della lezione."),
    ("struttura_quiz", "learning_quiz", "Struttura_Quiz", "Rinominata."),
    ("struttura_quiz_guidato", "learning_quesito (parte guidata)", "struttura_quiz_guidato", "Nuova, da separazione di learning_quesito."),
    ("struttura_quiz_finale", "learning_quesito (parte finale)", "struttura_quiz_finale", "Nuova, da separazione di learning_quesito."),
    ("learning_progresso", "—", "—", "Invariata. Popolata dagli utenti, non dal workbook."),
    ("learning_user", "—", "—", "Invariata."),
    ("learning_importanza", "learning_importanza", "— (eliminata)", "ELIMINATA con la colonna learning_lezione.priorita."),
]

NOTA_PREREQUISITI = (
    "La regola «ultime cifre dell'ID meno 1» e' stata verificata su tutti i 119 archi esistenti: riproduce il dato "
    "esattamente in 64 casi su 96. Non copre 22 lezioni con piu' di un prerequisito, 18 archi fra aree diverse "
    "(COM-A1-001 richiede GRA-A1-003) e 15 lezioni con suffisso -001 (genererebbe -000, inesistente); in un caso "
    "inverte la dipendenza (COM-A1-002 richiede COM-A1-004). Eliminare la tabella avrebbe perso 55 archi su 119 e reso "
    "inutilizzabile la validazione del DAG in services.py. La logica e' comunque disponibile come campo derivato "
    "Lezione.prerequisito_derivato, esposto in API e mostrato nel frontend come «Segue X», senza impatti sullo schema."
)


def _scrivi_foglio(wb, nome, titolo, sottotitolo, righe, posizione=None):
    if nome in wb.sheetnames:
        del wb[nome]
    ws = wb.create_sheet(nome) if posizione is None else wb.create_sheet(nome, posizione)
    ws["A1"] = titolo
    ws["A1"].font = TITLE
    ws["A2"] = sottotitolo
    ws["A2"].font = SUB
    ws["A2"].alignment = WRAP
    ws.row_dimensions[2].height = 30
    for i, intestazione in enumerate(COLS, start=1):
        cella = ws.cell(row=4, column=i, value=intestazione)
        cella.font, cella.fill, cella.alignment = HEAD, FILL, WRAP
    for r, riga in enumerate(righe, start=5):
        for i, valore in enumerate(riga, start=1):
            cella = ws.cell(row=r, column=i, value=valore)
            cella.font, cella.alignment = BODY, WRAP
    for i, larghezza in enumerate(WIDTHS, start=1):
        ws.column_dimensions[get_column_letter(i)].width = larghezza
    ws.freeze_panes = "A5"
    return ws


def _elimina_colonna(ws, intestazione, riga_intestazioni=4):
    valori = [c.value for c in ws[riga_intestazioni]]
    if intestazione in valori:
        ws.delete_cols(valori.index(intestazione) + 1)
        return True
    return False


def aggiorna(percorso):
    wb = load_workbook(percorso)
    modifiche = []

    if "Liste" in wb.sheetnames:
        ws = wb["Liste"]
        if _elimina_colonna(ws, "Importanza MVP"):
            modifiche.append("Liste: rimossa colonna «Importanza MVP»")
        ws["A2"] = (
            "Queste colonne alimentano le convalide dati degli altri fogli. Ogni colonna corrisponde a una tabella "
            "su Neon: Area Didattica → mapping_area_lezione, Tipologia Lezione → mapping_tipologia, "
            "Livello Linguistico → mapping_livello, Difficoltà → mapping_difficolta_lezione, "
            "Stato della Lezione → learning_statolezione."
        )

    if "Percorso MVP" in wb.sheetnames:
        ws = wb["Percorso MVP"]
        if _elimina_colonna(ws, "Importanza"):
            modifiche.append("Percorso MVP: rimossa colonna «Importanza»")
        for cella in ws[4]:
            if cella.value == "Motivazione della Priorità":
                cella.value = "Motivazione della Scelta"
                modifiche.append("Percorso MVP: «Motivazione della Priorità» → «Motivazione della Scelta»")
        ws["A2"] = (
            "Le lezioni del percorso MVP. L'ordine è dato da «Ordine MVP» (learning_lezione.ordine_mvp): la "
            "classificazione Essenziale/Consigliata/Secondaria è stata rimossa dal modello dati insieme alla "
            "tabella learning_importanza."
        )

    for nome, (titolo, sottotitolo, righe) in SHEETS.items():
        _scrivi_foglio(wb, nome, titolo, sottotitolo, righe)
    modifiche.append("Aggiunti/aggiornati 4 fogli di struttura")

    ws = _scrivi_foglio(
        wb, "Modello Dati",
        "MODELLO DATI — corrispondenza fogli / tabelle Neon",
        "Stato dopo la migration learning.0006. Se una struttura cambia su Neon va aggiornata anche qui.",
        MODELLO_DATI, posizione=1,
    )
    for i, intestazione in enumerate(["Tabella Neon (attuale)", "Nome precedente", "Foglio di riferimento", "Note"], start=1):
        cella = ws.cell(row=4, column=i, value=intestazione)
        cella.font, cella.fill, cella.alignment = HEAD, FILL, WRAP
    riga = len(MODELLO_DATI) + 6
    ws.cell(row=riga, column=1, value="Perché learning_prerequisito non è stata eliminata").font = Font(name="Arial", size=11, bold=True)
    cella = ws.cell(row=riga + 1, column=1, value=NOTA_PREREQUISITI)
    cella.font, cella.alignment = BODY, WRAP
    ws.merge_cells(start_row=riga + 1, start_column=1, end_row=riga + 5, end_column=4)
    for colonna, larghezza in zip("ABCD", [30, 34, 46, 74]):
        ws.column_dimensions[colonna].width = larghezza
    modifiche.append("Aggiunto foglio «Modello Dati»")

    wb.save(percorso)
    return modifiche


if __name__ == "__main__":
    for percorso in sys.argv[1:]:
        print(f"\n{percorso}")
        for voce in aggiorna(percorso):
            print(f"  - {voce}")
