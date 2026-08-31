import { useState } from 'react'
import { api } from '../api'
import { AREA } from '../constants'
import { useAuth } from '../context/AuthContext'
import { useLoad } from '../hooks/useLoad'
import { groupByAreaAndCategoria, groupByCategoria } from '../utils/grouping'
import LessonCard from '../components/LessonCard'
import { Loader, ErrorState } from '../components/Feedback'

// Catalogo completo delle lezioni (rotta "/lezioni") con filtri a cascata
// Area → Categoria e raggruppamenti che si adattano al filtro attivo.

 // !! Note:
 // Dobbiamo immaginare Lesson come un oggetto con queste proprietà: e tutte le variabili sotto (ueser, loading)
export default function Lessons() {
  const { user } = useAuth()
  // Crea questa costante con questi 3 dati all'intero
  // useLoad è un assitente che serve per far una telefono al serve (github o altri strumenti) e prendere i dati, in questo caso le lezioni.
  // in prima battuta abremo quindi 
     // loading = true, data = null, error = null, viene creato il componente Loader che mostra un messaggio di caricamento, e se c'è un errore viene creato il componente ErrorState che mostra il messaggio di errore.
  const { loading, data, error } = useLoad(() => api('/lezioni/indice/'))
  const [area, setArea] = useState('TUTTE')
  const [categoria, setCategoria] = useState('TUTTE')
  // Se stiamo ancora caricando i dati, mostriamo il componente Loader
  if (loading) return <Loader />
  // Se c'è stato un errore, mostriamo il componente ErrorState con il messaggio di errore
  if (error) return <ErrorState message={error} />

  const lessons = Object.entries(data).flatMap(([code, items]) => items.map(item => ({ ...item, area: code })))
  const assignedCount = lessons.filter(item => item.assegnata).length

  // Il filtro Categoria è a cascata: dipende dall'area selezionata.
  const selectArea = (code) => { setArea(code); setCategoria('TUTTE') }
  const categoriesForArea = area === 'TUTTE'
    ? []
    : [...new Set(lessons.filter(l => l.area === area).map(l => l.categoria).filter(Boolean))]

  let filtered = lessons
  if (area !== 'TUTTE') filtered = filtered.filter(l => l.area === area)
  if (categoria !== 'TUTTE') filtered = filtered.filter(l => l.categoria === categoria)

  // Con "Tutte" le lezioni si vedono raggruppate su due livelli (Macro argomento → Categoria).
  // Quando è selezionata un'area ma non una categoria specifica, restano raggruppate per
  // categoria soltanto (l'area è già implicita nel filtro attivo).
  const groupedByArea = area === 'TUTTE'
  const groupedByCategoria = area !== 'TUTTE' && categoria === 'TUTTE'

  return <div className="page">
    <div className="page-heading">
      <div>
        <h1>Tutte le lezioni</h1>
        <p>{user
          ? 'Consulta ogni lezione, assegnala al tuo percorso quando vuoi e tieni traccia dei progressi.'
          : "Consultabili gratuitamente, senza account. Registrati per assegnarle al tuo percorso e salvare i progressi."}</p>
      </div>
      {user && <div className="progress-ring" role="img" aria-label={`${assignedCount} lezioni nel tuo percorso`}>
        <strong>{assignedCount}</strong><span><center>lezioni salvate</center></span>
      </div>}
    </div>

    <div className="filters">
      <div className="filter-row" role="group" aria-label="Filtra per area">
        <button type="button" className={`filter-chip ${area === 'TUTTE' ? 'active' : ''}`} aria-pressed={area === 'TUTTE'} onClick={() => selectArea('TUTTE')}>Tutte</button>
        {Object.entries(AREA).map(([code, info]) => (
          <button
            key={code}
            type="button"
            className={`filter-chip ${info.className} ${area === code ? 'active' : ''}`}
            aria-pressed={area === code}
            onClick={() => selectArea(code)}
          >{info.label}</button>
        ))}
      </div>
      {categoriesForArea.length > 0 && (
        <div className="filter-row filter-row-sub" role="group" aria-label="Filtra per categoria">
          <span className="filter-label" aria-hidden="true">Categoria</span>
          <button type="button" className={`filter-chip ${categoria === 'TUTTE' ? 'active' : ''}`} aria-pressed={categoria === 'TUTTE'} onClick={() => setCategoria('TUTTE')}>Tutte le categorie</button>
          {categoriesForArea.map(cat => (
            <button
              key={cat}
              type="button"
              className={`filter-chip ${categoria === cat ? 'active' : ''}`}
              aria-pressed={categoria === cat}
              onClick={() => setCategoria(cat)}
            >{cat}</button>
          ))}
        </div>
      )}
    </div>

    {filtered.length === 0 && <p className="empty">Nessuna lezione con questi filtri.</p>}

    {groupedByArea
      ? groupByAreaAndCategoria(filtered).map(({ code, info, categorie }) => (
          <section key={code} className={`lesson-area-group ${info.className}`} aria-label={info.label}>
            <h2 className="lesson-area-heading">
              {info.label} <span className="lesson-group-count">{categorie.reduce((n, g) => n + g.items.length, 0)}</span>
            </h2>
            {categorie.map(({ categoria: cat, items }) => (
              <section key={cat} className="lesson-group" aria-label={cat}>
                <h3 className="lesson-group-heading">{cat} <span className="lesson-group-count">{items.length}</span></h3>
                <ul className="lesson-list">
                  {items.map((lesson, index) => (
                    <li key={lesson.id}><LessonCard lesson={lesson} index={index} user={user} /></li>
                  ))}
                </ul>
              </section>
            ))}
          </section>
        ))
      : groupedByCategoria
      ? groupByCategoria(filtered).map(({ categoria: cat, items }) => (
          <section key={cat} className="lesson-group" aria-label={cat}>
            <h2 className="lesson-group-heading">{cat} <span className="lesson-group-count">{items.length}</span></h2>
            <ul className="lesson-list">
              {items.map((lesson, index) => (
                <li key={lesson.id}><LessonCard lesson={lesson} index={index} user={user} /></li>
              ))}
            </ul>
          </section>
        ))
      : <ul className="lesson-list" aria-label="Elenco lezioni">
          {filtered.map((lesson, index) => (
            <li key={lesson.id}><LessonCard lesson={lesson} index={index} user={user} /></li>
          ))}
        </ul>}
  </div>
}
