// Questo è il PRIMO file JavaScript che viene eseguito nel browser.
// Vite lo inietta nell'unico file HTML (index.html), che contiene solo <div id="root"></div>:
// è per questo che "il server consegna un HTML quasi vuoto" — il contenuto lo disegna questo script.
import React from 'react'
import ReactDOM from 'react-dom/client'

// BrowserRouter legge l'URL corrente (es. /login) e decide quale pagina mostrare,
// Serve per la navigazione (Single Page Application). Con questo comando tutte le pagine sono in realtà componenti React che vengono montati e smontati dinamicamente.
import { BrowserRouter } from 'react-router-dom'
// App (src/App.jsx) è il componente radice: definisce la mappa delle rotte
// (URL → pagina di src/pages/) dentro il Layout condiviso (navbar + footer).
import App from './App'
// styles.css contiene le regole CSS globali, che si applicano a tutta l'applicazione.
import './styles.css'

// document.getElementById('root') trova il <div> vuoto nell'HTML.
// createRoot(...).render(...) monta l'albero di componenti React dentro quel div:
// da qui in poi tutta la UI (navbar, pagine, form) è generata da JavaScript.
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode><BrowserRouter><App /></BrowserRouter></React.StrictMode>,
)

