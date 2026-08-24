import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

// La navbar in cima a ogni pagina. Cambia in base a chi sta guardando:
// mostra link diversi per visitatore anonimo, utente loggato e amministratore.
export default function Header() {
  // Legge dal Context globale se c'è un utente loggato (vedi AuthProvider).
  // Questa riga è la risposta a "come fa il programma a sapere che nessuno ha
  // effettuato l'accesso": user è null finché non esiste un login salvato.
  const { user, logout } = useAuth()
  return <header className="topbar">
    <Link className="brand" to="/"><span className="brand-mark" aria-hidden="true">PC</span> Prima conversazione</Link>
    <nav aria-label="Navigazione principale">
      {/* Home e Lezioni sono sempre pubbliche: compaiono per chiunque, loggato o no. */}
      <Link to="/">Home</Link>
      <Link to="/lezioni">Lezioni</Link>
      {/* Rendering condizionale: `user && <Link .../>` in JSX significa
          "disegna il link SOLO se `user` non è null/undefined". Ecco perché,
          al primo arrivo sul sito (user === null), Progressi e Profilo
          semplicemente non vengono generati nell'HTML — non sono nascosti
          con CSS, non esistono proprio nel DOM. */}
      {user && <Link to="/progressi">Progressi</Link>}
      {/* Ulteriore condizione sul singolo campo is_staff dell'utente: link
          visibile solo agli amministratori, oltre che solo ai loggati. */}
      {user?.is_staff && <Link to="/contenuti-da-completare">Contenuti</Link>}
      {user && <Link to="/profilo">Profilo</Link>}
      {/* Stesso principio applicato al blocco destro della navbar: o mostri
          "Esci" (loggato) oppure "Accedi" + "Registrati" (anonimo) — mai entrambi. */}
      {user
        ? <button type="button" className="link-button" onClick={logout}>Esci</button>
        : <>
          <Link to="/login">Accedi</Link>
          <Link className="nav-cta" to="/registrati">Registrati</Link>
        </>}
    </nav>
  </header>
}
