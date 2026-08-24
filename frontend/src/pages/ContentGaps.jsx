import { Navigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'
import { useLoad } from '../hooks/useLoad'
import { Loader, ErrorState } from '../components/Feedback'

// Pannello amministrativo (rotta "/contenuti-da-completare") che elenca le lezioni
// con contenuti mancanti. Riservato allo staff: un non-admin viene rimandato alle lezioni.
export default function ContentGaps() {
  const { user } = useAuth()
  const { loading, data, error } = useLoad(() => api('/admin/contenuti-mancanti/'))
  if (!user.is_staff) return <Navigate to="/lezioni" replace />
  if (loading) return <Loader />
  if (error) return <ErrorState message={error} />
  return <div className="page">
    <h1>Contenuti da completare</h1>
    <div className="summary-grid">
      <div><strong>{data.riepilogo.lezioni_mvp}</strong><span>lezioni MVP</span></div>
      <div><strong>{data.riepilogo.sezioni_todo}</strong><span>sezioni TODO</span></div>
      <div><strong>{data.riepilogo.quiz_finali_mancanti}</strong><span>quiz finali mancanti</span></div>
    </div>
    <ul className="gap-list" aria-label="Lezioni con contenuti mancanti">
      {data.lezioni.map(lesson => <li key={lesson.id}><article>
        <div>
          <span className="lesson-meta">{lesson.area} · ordine {lesson.ordine_mvp}</span>
          <h2>{lesson.nome}</h2>
          <small>{lesson.id} · {lesson.stato_sorgente}</small>
        </div>
        <div>
          <b>{lesson.sezioni_todo.length} sezioni TODO</b>
          <span>{lesson.quiz_finale_mancante ? 'Quiz finale mancante' : 'Quiz finale presente'}</span>
        </div>
      </article></li>)}
    </ul>
  </div>
}
