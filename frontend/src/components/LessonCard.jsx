import { Link } from 'react-router-dom'
import { AREA } from '../constants'
import StatusPill from './StatusPill'

// Card che rappresenta una lezione nell'elenco. Cambia aspetto se la lezione è
// "in preparazione" e mostra stato/assegnazione solo agli utenti loggati.
export default function LessonCard({ lesson, index, user }) {
  const area = AREA[lesson.area] || AREA.GRA
  const inPrep = lesson.in_preparazione
  const cardClass = `lesson-card ${area.className} ${inPrep ? 'in-prep' : ''}`.trim()
  return <article className={cardClass} style={{ '--i': index }} aria-labelledby={`lc-${lesson.id}`}>
    <div className={`area-icon ${area.className}`} aria-hidden="true">
      {inPrep ? '…' : area.icon}
    </div>
    <div className="lesson-order" aria-hidden="true">{String(lesson.ordine_percorso).padStart(2, '0')}</div>
    <div className="lesson-main">
      <div className="lesson-meta">
        <span>{area.label}</span>
        {lesson.categoria && <span>{lesson.categoria}</span>}
        <span>{lesson.livello}</span>
        <span>{lesson.durata_min} min</span>
      </div>
      <h2 id={`lc-${lesson.id}`}>{lesson.nome}</h2>
      <p>{lesson.descrizione}</p>
      {inPrep && (
        <p className="in-prep-note">Struttura editoriale definita, contenuti in arrivo.</p>
      )}
    </div>
    <div className="lesson-action">
      {user && lesson.stato && <StatusPill status={lesson.stato} />}
      {user && lesson.assegnata && <span className="status assegnata">Nel percorso</span>}
      {!inPrep && (
        <Link className="arrow" aria-label={`Apri ${lesson.nome}`} to={`/lezioni/${lesson.id}`}>→</Link>
      )}
      {inPrep && (
        <Link className="arrow prep" aria-label={`Apri anteprima di ${lesson.nome}`} to={`/lezioni/${lesson.id}`}>i</Link>
      )}
    </div>
  </article>
}
