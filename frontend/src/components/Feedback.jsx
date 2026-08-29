import { Link } from 'react-router-dom'

// Piccoli componenti di stato riusati da quasi tutte le pagine mentre caricano
// i dati o incontrano un errore. Stanno insieme perché sono due facce della
// stessa cosa: "cosa mostrare quando non c'è ancora il contenuto vero".

export const Loader = () => <div className="loader" role="status" aria-live="polite">Caricamento…</div>

// Esporta questa variabile per poterla usare in altri componenti
// che cosa devi esporta il messaggio
// => singnigica prendi il messaggio di prima e mettilo dentro la classe <div className="error-state">
export const ErrorState = ({ message }) => <div className="error-state">
  <h2>Qualcosa non ha funzionato</h2>
  <p>{message}</p>
  <Link to="/lezioni">Torna alle lezioni</Link>
</div>
