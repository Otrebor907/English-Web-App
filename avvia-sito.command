#!/bin/bash
# =====================================================================
#  AVVIA IL SITO — English Web App
#  Doppio clic su questo file: avvia backend + frontend, aspetta che
#  siano davvero pronti e apre il sito nel browser.
#  Per spegnere tutto: premi Ctrl + C in questa finestra.
# =====================================================================

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$REPO/.venv/bin/python"
LOGS="$REPO/.logs"
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

mkdir -p "$LOGS"

# Se qualcosa va storto, la finestra resta aperta per farti leggere l'errore
muori() {
  echo ""
  echo "-----------------------------------------------------------"
  echo "$1"
  echo "-----------------------------------------------------------"
  echo ""
  echo "Premi INVIO per chiudere."
  read -r
  exit 1
}

echo "Avvio del sito English Web App..."
echo "Cartella progetto: $REPO"
echo ""

# --- Controlli preliminari -------------------------------------------
[ -x "$PY" ] || muori "ERRORE: manca l'ambiente Python in $REPO/.venv
Apri il Terminale in questa cartella ed esegui:
   python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt"

[ -d "$REPO/frontend/node_modules" ] || muori "ERRORE: mancano le dipendenze del frontend.
Apri il Terminale in questa cartella ed esegui:
   cd frontend && npm install"

if command -v pnpm >/dev/null 2>&1; then
  DEV_CMD="pnpm dev"
elif command -v npm >/dev/null 2>&1; then
  DEV_CMD="npm run dev"
else
  muori "ERRORE: non trovo ne' pnpm ne' npm. Installa Node.js da https://nodejs.org"
fi

# Porte gia' occupate da un avvio precedente rimasto acceso?
for PORTA in 8000 5173; do
  if lsof -iTCP:$PORTA -sTCP:LISTEN >/dev/null 2>&1; then
    muori "ERRORE: la porta $PORTA e' gia' occupata (forse il sito e' gia' acceso).
Chiudi l'altra finestra del sito, oppure esegui nel Terminale:
   lsof -ti tcp:$PORTA | xargs kill"
  fi
done

# --- Spegnimento pulito di tutto quando premi Ctrl + C ---------------
BACKEND_PID=""
FRONTEND_PID=""
spegni() {
  trap - EXIT INT TERM   # evita che il messaggio esca due volte
  echo ""
  echo "Spengo il sito..."
  for P in "$FRONTEND_PID" "$BACKEND_PID"; do
    if [ -n "$P" ] && kill -0 "$P" 2>/dev/null; then
      pkill -P "$P" 2>/dev/null
      kill "$P" 2>/dev/null
    fi
  done
  echo "Fatto. Puoi chiudere questa finestra."
}
trap spegni EXIT INT TERM

# --- 1) BACKEND (Django) ---------------------------------------------
echo "1/3  Preparo il database..."
if ! "$PY" "$REPO/backend/manage.py" migrate > "$LOGS/backend.log" 2>&1; then
  echo ""
  tail -20 "$LOGS/backend.log"
  muori "ERRORE durante la preparazione del database (vedi sopra).
Log completo: $LOGS/backend.log"
fi

echo "2/3  Avvio il backend (Django) su http://localhost:8000 ..."
"$PY" "$REPO/backend/manage.py" runserver >> "$LOGS/backend.log" 2>&1 &
BACKEND_PID=$!

# --- 2) FRONTEND (Vite/React) ----------------------------------------
echo "3/3  Avvio il frontend (React) su http://localhost:5173 ..."
cd "$REPO/frontend" || muori "ERRORE: non trovo la cartella $REPO/frontend"
$DEV_CMD > "$LOGS/frontend.log" 2>&1 &
FRONTEND_PID=$!

# --- 3) Aspetta che le porte rispondano davvero -----------------------
aspetta_porta() {
  local porta="$1" nome="$2" pid="$3" log="$4" i=0
  while [ $i -lt 60 ]; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo ""
      tail -20 "$log"
      muori "ERRORE: il $nome si e' chiuso subito (vedi sopra).
Log completo: $log"
    fi
    if lsof -iTCP:"$porta" -sTCP:LISTEN >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
    i=$((i + 1))
  done
  echo ""
  tail -20 "$log"
  muori "ERRORE: il $nome non ha risposto sulla porta $porta entro 30 secondi.
Log completo: $log"
}

echo ""
echo "Attendo che i server siano pronti..."
aspetta_porta 8000 "backend" "$BACKEND_PID" "$LOGS/backend.log"
echo "   backend pronto."
aspetta_porta 5173 "frontend" "$FRONTEND_PID" "$LOGS/frontend.log"
echo "   frontend pronto."

open "http://localhost:5173"

echo ""
echo "==================================================================="
echo "  Il sito e' acceso:  http://localhost:5173"
echo ""
echo "  Per SPEGNERE: premi  Ctrl + C  in questa finestra."
echo "  NON chiudere questa finestra mentre usi il sito."
echo "==================================================================="
echo ""

# Resta in ascolto: se uno dei due server muore, te ne accorgi qui
wait
