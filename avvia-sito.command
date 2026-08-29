#!/bin/bash
# =====================================================================
#  AVVIA IL SITO — English Web App
#  Doppio clic su questo file per avviare backend + frontend e aprire
#  il sito nel browser. Non serve chiedere niente a nessuno.
# =====================================================================


echo "Avvio del sito English Web App..."
echo "Cartella progetto: $REPO"
echo ""

# --- 1) BACKEND (Django) in una nuova finestra di Terminale ---
osascript -e "tell application \"Terminal\" to do script \"cd '$REPO/backend' && '$REPO/.venv/bin/python' manage.py migrate && '$REPO/.venv/bin/python' manage.py runserver\""

# --- 2) FRONTEND (Vite/React) in un'altra finestra di Terminale ---
osascript -e "tell application \"Terminal\" to do script \"cd '$REPO/frontend' && pnpm dev\""

# --- 3) Aspetta che i server partano e apri il browser ---
echo "Attendo qualche secondo che i server si avviino..."
sleep 8
open "http://localhost:5173"

echo ""
echo "Fatto. Se il browser non si apre da solo, controlla nella finestra"
echo "del FRONTEND l'indirizzo scritto accanto a 'Local:' (es. http://localhost:5173)"
echo "e aprilo a mano."
echo ""
echo "Per SPEGNERE il sito: vai in ciascuna delle due finestre di Terminale"
echo "e premi  Ctrl + C  (poi puoi chiuderle)."
