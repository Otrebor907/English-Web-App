import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'

/**
 * Un unico componente serve sia /login sia /registrati (vedi App.jsx):
 * la prop `register` cambia solo testi ed endpoint chiamato, la logica è identica.
 * Questo è il form che l'utente vede e compila per accedere.
 */
export default function Auth({ register = false }) {
  // Stato locale del form: cosa l'utente ha digitato finora.
  const [form, setForm] = useState({ email: '', nome: '', cognome: '', password: '' })
  // Messaggio di errore da mostrare (es. "Email o password non validi" dal backend).
  const [error, setError] = useState('')
  // Disabilita il bottone mentre la richiesta è in volo, per evitare doppi invii.
  const [busy, setBusy] = useState(false)
  // authenticate viene da AuthProvider: è la funzione che, a login riuscito,
  // salva token+utente e "accende" lo stato loggato in tutta l'app.
  const { authenticate } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  // Se si arriva qui da Protected (es. tentativo di aprire /profilo da anonimo),
  // l'URL contiene ?next=/profilo: dopo il login si torna a quella pagina.
  const next = new URLSearchParams(location.search).get('next') || '/lezioni'
  const nextQuery = next !== '/lezioni' ? `?next=${encodeURIComponent(next)}` : ''

  // Gestore dell'invio del form: qui avviene la VERA chiamata al backend.
  const submit = async (event) => {
    // Impedisce il comportamento di default del browser (ricaricare la pagina
    // e mandare i dati come form HTML classico) — vogliamo gestirlo noi via fetch.
    event.preventDefault(); setBusy(true); setError('')
    try {
      // api() (frontend/src/api.js) fa una POST JSON a:
      //   /api/auth/login/       se stiamo accedendo
      //   /api/auth/registrati/  se stiamo creando un account
      // Il corpo inviato è { email, password }. Il backend Django risponde con
      // { token, utente } se le credenziali sono corrette (vedi backend/learning/views.py).
      authenticate(await api(`/auth/${register ? 'registrati' : 'login'}/`, { method: 'POST', body: JSON.stringify(form) }))
      // Da questo momento AuthContext ha user valorizzato: la navbar (Layout)
      // si ri-renderizza da sola mostrando Progressi/Profilo/Esci.
      navigate(next)
    } catch (err) {
      // api() lancia un'eccezione con .data quando il backend risponde con errore
      // (es. 400 Bad Request). err.data.email/.password sono i messaggi di
      // validazione specifici restituiti dai serializer Django (es. "Email o password non validi").
      setError(err.data?.email?.[0] || err.data?.password?.[0] || err.message)
    } finally { setBusy(false) }
  }
  return <div className="auth-shell">
    <section className="auth-copy">
      <span className="eyebrow">INGLESE, SENZA ANSIA</span>
      <h1>Dalle basi alla tua <em>prima conversazione.</em></h1>
      <p>Un percorso chiaro, progettato intorno agli errori che facciamo più spesso noi italiani.</p>
    </section>
    <form className="auth-card" onSubmit={submit}>
      <h2>{register ? 'Crea il tuo profilo' : 'Bentornato'}</h2>
      <p>{register ? 'Inizia gratuitamente il percorso.' : 'Riprendi da dove eri rimasto.'}</p>
      {/* Ogni input è "controllato" da React: value viene dallo stato `form`,
          onChange lo aggiorna ad ogni tasto premuto (pattern standard dei form React). */}
      <label>Email<input type="email" required value={  form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></label>
      {/* Nome e cognome servono solo per la registrazione, non per il login. */}
      {register && (
        <>
          <label>Nome<input type="text" required value={form.nome} onChange={e => setForm({ ...form, nome: e.target.value })} /></label>
          <label>Cognome<input type="text" required value={form.cognome} onChange={e => setForm({ ...form, cognome: e.target.value })} /></label>
        </>
      )}
      <label>Password<input type="password" required minLength="8" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /></label>
      {error && <div className="alert" role="alert" aria-live="assertive">{error}</div>}
      <button className="primary" disabled={busy}>{busy ? 'Attendi…' : register ? 'Crea account' : 'Accedi'}</button>
      <small>{register ? 'Hai già un account?' : 'Non hai un account?'} <Link to={`${register ? '/login' : '/registrati'}${nextQuery}`}>{register ? 'Accedi' : 'Registrati'}</Link></small>
    </form>
  </div>
}
