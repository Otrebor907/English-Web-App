"""Client minimo della Management API di Neon (https://console.neon.tech/api/v2).

Serve a una cosa sola: gestire i branch usati come rete di sicurezza prima di un
import. Crea, elenca e cancella branch — niente altro.

ATTENZIONE, per non confondere due cose diverse: questa e' l'API di *controllo*
di Neon, quella che gestisce progetti e branch. NON e' la via con cui il
progetto legge e scrive i dati: per quelli si usa l'ORM di Django su
connessione Postgres diretta (psycopg), che da' transazioni atomiche e permette
ai test di girare su SQLite. Qui si amministra l'infrastruttura, non il
contenuto delle tabelle.

Usa urllib della standard library di proposito: nessuna dipendenza nuova in
requirements.txt per una manciata di chiamate HTTP.
"""
import json
import os
import urllib.error
import urllib.request

BASE_URL = "https://console.neon.tech/api/v2"
TIMEOUT = 30
# Tetto del piano Free: 10 branch per progetto, e su Free non se ne possono
# comprare di aggiuntivi. Serve a dare un errore comprensibile prima che sia
# Neon a rifiutare la creazione.
LIMITE_BRANCH_PIANO_FREE = 10

ISTRUZIONI_CREDENZIALI = (
    "Servono due variabili nel file .env alla radice del progetto:\n"
    "  NEON_API_KEY=napi_...   (console.neon.tech → Account settings → API keys → Create)\n"
    "  NEON_PROJECT_ID=...     (console.neon.tech → il progetto → Settings)\n"
    "La chiave viene mostrata una volta sola alla creazione: se la perdi, ne generi un'altra."
)


class NeonError(RuntimeError):
    """Qualunque cosa vada storta parlando con Neon."""


def _credenziali():
    chiave = os.getenv("NEON_API_KEY")
    progetto = os.getenv("NEON_PROJECT_ID")
    mancanti = [nome for nome, valore in (("NEON_API_KEY", chiave), ("NEON_PROJECT_ID", progetto)) if not valore]
    if mancanti:
        raise NeonError(f"Credenziali Neon mancanti: {', '.join(mancanti)}.\n{ISTRUZIONI_CREDENZIALI}")
    return chiave, progetto


def _richiesta(metodo, percorso, corpo=None):
    chiave, progetto = _credenziali()
    url = f"{BASE_URL}/projects/{progetto}{percorso}"
    dati = json.dumps(corpo).encode("utf-8") if corpo is not None else None
    richiesta = urllib.request.Request(
        url, data=dati, method=metodo,
        headers={
            "Authorization": f"Bearer {chiave}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(richiesta, timeout=TIMEOUT) as risposta:
            grezzo = risposta.read()
            return json.loads(grezzo) if grezzo else {}
    except urllib.error.HTTPError as errore:
        dettaglio = errore.read().decode("utf-8", "replace")[:400]
        if errore.code in (401, 403):
            raise NeonError(
                f"Neon ha rifiutato le credenziali (HTTP {errore.code}). "
                f"Controlla NEON_API_KEY e che la chiave veda il progetto NEON_PROJECT_ID.\n{dettaglio}"
            ) from errore
        if errore.code == 404:
            raise NeonError(
                f"Neon non trova la risorsa (HTTP 404) su {metodo} {percorso}. "
                f"NEON_PROJECT_ID e' corretto?\n{dettaglio}"
            ) from errore
        raise NeonError(f"Neon ha risposto HTTP {errore.code} a {metodo} {percorso}: {dettaglio}") from errore
    except urllib.error.URLError as errore:
        raise NeonError(f"Neon irraggiungibile ({errore.reason}). Connessione di rete assente o bloccata?") from errore


def elenca_branch():
    """Tutti i branch del progetto, come li restituisce Neon."""
    return _richiesta("GET", "/branches").get("branches", [])


def branch_predefinito(branch=None):
    """Il branch di default del progetto: il genitore da cui si dirama il backup."""
    branch = branch if branch is not None else elenca_branch()
    for riga in branch:
        if riga.get("default") or riga.get("primary"):
            return riga
    raise NeonError("Nessun branch predefinito trovato nel progetto Neon.")


def crea_branch(nome, parent_id):
    """Crea un branch SENZA compute.

    Omettere la chiave "endpoints" e' voluto: un branch di backup non deve
    essere interrogabile, deve solo esistere. Senza compute non consuma
    CU-hours, e lo spazio resta vicino a zero finche' nessuno ci scrive
    (i branch figli sono copy-on-write).
    """
    risposta = _richiesta("POST", "/branches", {"branch": {"name": nome, "parent_id": parent_id}})
    return risposta.get("branch", {})


def cancella_branch(branch_id):
    return _richiesta("DELETE", f"/branches/{branch_id}")
