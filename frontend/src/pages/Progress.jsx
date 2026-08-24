import { Link } from 'react-router-dom'
import { api } from '../api'
import { useLoad } from '../hooks/useLoad'
import StatusPill from '../components/StatusPill'
import { Loader, ErrorState } from '../components/Feedback'

// Riepilogo dei progressi dell'utente sulle lezioni assegnate (rotta "/progressi",
// riservata ai loggati tramite <Protected> in App.jsx).
export default function Progress() {
  const { loading, data, error } = useLoad(() => api('/progressi/'))
  if (loading) return <Loader />
  if (error) return <ErrorState message={error} />
  return <div className="page narrow">
    <h1>Progressi</h1>
    {data.length === 0
      ? <div className="empty">Non hai ancora assegnato nessuna lezione al tuo percorso. <Link to="/lezioni">Esplora le lezioni</Link> e aggiungi quelle che ti interessano.</div>
      : <ul className="progress-list" aria-label="Elenco progressi">
          {data.map(item => <li key={item.lezione_id}><article>
            <div><h3>{item.lezione_nome}</h3><StatusPill status={item.stato} /></div>
            <strong>{item.punteggio}%</strong>
          </article></li>)}
        </ul>}
  </div>
}
