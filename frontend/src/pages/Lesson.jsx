import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { api } from '../api'
import { AREA } from '../constants'
import { useAuth } from '../context/AuthContext'
import { useLoad } from '../hooks/useLoad'
import SectionList from '../components/Section'
import StatusPill from '../components/StatusPill'
import QuizView from '../components/QuizView'
import InPreparationLesson from '../components/InPreparationLesson'
import { Loader, ErrorState } from '../components/Feedback'

// Pagina di una singola lezione (rotta "/lezioni/:id"): contenuto, assegnazione
// al percorso ed esercizi. Gli esercizi sono accessibili solo agli utenti loggati.
export default function Lesson() {
  const { id } = useParams()
  const { user } = useAuth()
  const location = useLocation()
  const { loading, data: lesson, error } = useLoad(() => api(`/lezioni/${id}/`), [id])
  const [quizIndex, setQuizIndex] = useState(-1)
  const [assigned, setAssigned] = useState(false)
  const [assignBusy, setAssignBusy] = useState(false)

  useEffect(() => { setAssigned(Boolean(lesson?.assegnata)) }, [lesson?.id, lesson?.assegnata])

  useEffect(() => {
    if (user && lesson && !lesson.in_preparazione) {
      api(`/lezioni/${id}/inizia/`, { method: 'POST' }).catch(() => {})
    }
  }, [id, lesson, user])

  if (loading) return <Loader />
  if (error) return <ErrorState message={error} />
  if (lesson.in_preparazione) return <InPreparationLesson lesson={lesson} />

  const area = AREA[lesson.area] || AREA.GRA
  const hasSections = lesson.sezioni?.length > 0
  const hasQuiz = lesson.quiz?.length > 0
  const nextParam = `?next=${encodeURIComponent(location.pathname)}`

  const toggleAssign = async () => {
    setAssignBusy(true)
    try {
      const data = await api(`/lezioni/${id}/assegna/`, { method: assigned ? 'DELETE' : 'POST' })
      setAssigned(Boolean(data.assegnata))
    } finally { setAssignBusy(false) }
  }

  return <div className={`lesson-page ${area.className}`}>
    <div className="lesson-hero">
     <div className="lesson-hero-inner">
      <Link className="back" to="/lezioni">← Lezioni</Link>
      <span className="eyebrow">{area.label} · {lesson.livello}{lesson.categoria ? ` · ${lesson.categoria}` : ''}</span>
      <h1>{lesson.nome}</h1>
      <p>{lesson.obiettivo_didattico}</p>
      <div className="hero-meta" aria-label="Dettagli lezione">
        <span>{lesson.durata_min} min</span>
        {lesson.difficolta && <span>Difficoltà {lesson.difficolta}</span>}
        {lesson.prerequisito_derivato && <span>Segue {lesson.prerequisito_derivato}</span>}
      </div>
      {user && (
        <div className="assign-control">
          {assigned
            ? <>
              <span className="assign-confirm" role="status">✓ Aggiunta alle mie lezioni</span>
              <button type="button" className="secondary" onClick={toggleAssign} disabled={assignBusy}>
                {assignBusy ? 'Attendi…' : 'Rimuovi dalle mie lezioni'}
              </button>
            </>
            : <button type="button" className="primary" onClick={toggleAssign} disabled={assignBusy}>
              {assignBusy ? 'Attendi…' : 'Aggiungi alle mie lezioni'}
            </button>}
          <span className="assign-meta">
            <StatusPill status={lesson.stato_utente || 'disponibile'} />
            {lesson.ultimo_risultato != null && <span className="assign-score">Ultimo risultato: {lesson.ultimo_risultato}%</span>}
          </span>
        </div>
      )}
     </div>
    </div>
    <div className="lesson-content">
      {hasSections && <SectionList sezioni={lesson.sezioni} />}
      <div className="exercise-section">
        <h2 className="exercise-heading">Esercizio</h2>
        {!hasQuiz && (
          <section className="quiz-card empty">
            <h2>Quiz in preparazione</h2>
            <p>Le esercitazioni per questa lezione non sono ancora disponibili.</p>
          </section>
        )}
        {hasQuiz && (
          <div className="exercise-wrap">
            {!user && (
              <div className="exercise-gate" role="region" aria-label="Registrazione richiesta per esercitarsi">
                <p>Per esercitarti, salvare i progressi e assegnarti le lezioni, registrati gratuitamente.</p>
                <div className="exercise-gate-actions">
                  <Link className="primary" to={`/registrati${nextParam}`}>Registrati</Link>
                  <Link className="secondary" to={`/login${nextParam}`}>Hai già un account? Accedi</Link>
                </div>
              </div>
            )}
            <div
              className="quiz-launch" role="group" aria-label="Esercitazioni disponibili"
              inert={!user} aria-hidden={!user}
            >
              <h3>È il momento di provare</h3>
              <p>Inizia dall'esercizio guidato, poi affronta il quiz finale.</p>
              <div className="quiz-launch-buttons">
                {lesson.quiz.map((quiz, i) => (
                  <button
                    key={quiz.id}
                    type="button"
                    disabled={!user}
                    className={quiz.modalita === 'finale' ? 'primary' : 'secondary'}
                    onClick={() => setQuizIndex(i)}
                    aria-pressed={quizIndex === i}
                  >{quiz.titolo}</button>
                ))}
              </div>
            </div>
          </div>
        )}
        {user && quizIndex >= 0 && hasQuiz && (
          <QuizView
            quiz={lesson.quiz[quizIndex]}
            lessonId={id}
            onComplete={(data) => {
              if (data?.superato) setAssigned(true)
              if (quizIndex < lesson.quiz.length - 1) setQuizIndex(quizIndex + 1)
            }}
          />
        )}
      </div>
    </div>
  </div>
}
