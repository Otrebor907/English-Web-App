import { Link } from 'react-router-dom'
import { AREA } from '../constants'

// Vista mostrata al posto della lezione quando questa è ancora "in preparazione":
// la struttura editoriale esiste ma i contenuti definitivi non sono pubblicati.
export default function InPreparationLesson({ lesson }) {
  const area = AREA[lesson.area] || AREA.GRA
  return <div className={`lesson-page ${area.className}`}>
    <div className="lesson-hero">
     <div className="lesson-hero-inner">
      <Link className="back" to="/lezioni">← Lezioni</Link>
      <span className="eyebrow">{area.label} · {lesson.livello}{lesson.categoria ? ` · ${lesson.categoria}` : ''}</span>
      <h1>{lesson.nome}</h1>
      <p>{lesson.descrizione}</p>
     </div>
    </div>
    <div className="lesson-content in-prep-shell">
      <div className="in-prep-card" role="status" aria-live="polite">
        <span className="eyebrow">CONTENUTO IN PREPARAZIONE</span>
        <h2>Questa lezione è in preparazione</h2>
        <p>La struttura editoriale c'è, ma i contenuti definitivi (esempi, spiegazioni, esercizi e quiz) non sono ancora stati pubblicati. Torna a breve.</p>
        <dl className="in-prep-meta">
          <div><dt>Obiettivo</dt><dd>{lesson.obiettivo_didattico || '—'}</dd></div>
          <div><dt>Durata prevista</dt><dd>{lesson.durata_min} min</dd></div>
          {lesson.competenze?.length ? <div><dt>Competenze</dt><dd>{lesson.competenze.join(', ')}</dd></div> : null}
          {lesson.errori_tipici?.length ? <div><dt>Errori tipici</dt><dd>{lesson.errori_tipici.join('; ')}</dd></div> : null}
        </dl>
        <Link className="primary" to="/lezioni">Torna alle lezioni</Link>
      </div>
    </div>
  </div>
}
