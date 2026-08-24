import { Link } from 'react-router-dom'
import { api } from '../api'
import { AREA } from '../constants'
import { useLoad } from '../hooks/useLoad'
import { groupByCategoria } from '../utils/grouping'

// Barra laterale con l'elenco completo delle lezioni, raggruppate per area e
// categoria. Mostrata su tutte le pagine tranne home e autenticazione (vedi Layout).
export default function LessonSidebar() {
  const { data } = useLoad(() => api('/lezioni/indice/'))
  if (!data) return null
  return <nav className="side-nav" aria-label="Elenco completo delle lezioni">
    {Object.entries(AREA).map(([code, area]) => {
      const lessons = data[code] || []
      if (!lessons.length) return null
      return <details key={code} className="side-group">
        <summary>
          <span>{area.label}</span>
          <span className="side-count" aria-hidden="true">{lessons.length}</span>
        </summary>
        {groupByCategoria(lessons).map(({ categoria, items }) => (
          <details key={categoria} className="side-subgroup" open>
            <summary>
              <span className="side-subgroup-name">{categoria}</span>
              <span className="side-count" aria-hidden="true">{items.length}</span>
            </summary>
            <ul>
              {items.map(lesson => (
                <li key={lesson.id}>
                  <Link className="side-link" to={`/lezioni/${lesson.id}`}>
                    <span className="side-link-order" aria-hidden="true">{String(lesson.ordine_percorso).padStart(2, '0')}</span>
                    <span className="side-link-name">{lesson.nome}</span>
                    {lesson.stato === 'completata' && <span className="side-link-flag done" aria-label="Completata">✓</span>}
                    {lesson.in_preparazione && <span className="side-link-flag prep" aria-label="In preparazione">…</span>}
                  </Link>
                </li>
              ))}
            </ul>
          </details>
        ))}
      </details>
    })}
  </nav>
}
