import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { useCountUp } from '../hooks/useCountUp'

// Schermata di riepilogo mostrata al termine del quiz finale, con il punteggio animato.
function ResultCard({ result }) {
  const animatedScore = useCountUp(result.punteggio)
  return <section className="quiz-result" aria-live="polite">
    <span aria-hidden="true">
      {result.superato ? '✓' : '↻'}
      {result.superato && <span className="star-burst" aria-hidden="true" />}
    </span>
    <h2>{animatedScore}%</h2>
    <p>{result.superato ? 'Quiz superato! La lezione è completata.' : 'Riprova: serve almeno il 70%.'}</p>
    <small>Miglior punteggio: {result.miglior_punteggio}%</small>
  </section>
}

// Svolgimento interattivo di un quiz: naviga tra i quesiti, verifica le risposte
// con il backend e, per il quiz finale, calcola il punteggio finale.
export default function QuizView({ quiz, lessonId, onComplete }) {
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState({})
  const [feedback, setFeedback] = useState({})
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const questionHeadingRef = useRef(null)
  const question = quiz.quesiti[index]
  const total = quiz.quesiti.length
  const isFinal = quiz.modalita === 'finale'

  useEffect(() => {
    if (questionHeadingRef.current) questionHeadingRef.current.focus()
  }, [index, result])

  if (!question || total === 0) {
    return <section className="quiz-card empty" aria-live="polite">
      <span className="eyebrow">{isFinal ? 'QUIZ FINALE' : 'ESERCIZIO GUIDATO'}</span>
      <h2>Quiz in preparazione</h2>
      <p>Torna presto: i quesiti verranno pubblicati insieme al contenuto definitivo.</p>
    </section>
  }

  if (result) {
    return <ResultCard result={result} />
  }

  const answer = answers[question.id] || ''
  const checked = feedback[question.id]

  const verify = async () => {
    setBusy(true)
    try {
      const data = await api(`/lezioni/${lessonId}/quiz/${quiz.modalita}/quesiti/${question.id}/verifica/`, {
        method: 'POST', body: JSON.stringify({ risposta: answer }),
      })
      setFeedback({ ...feedback, [question.id]: data })
    } finally { setBusy(false) }
  }

  const finish = async () => {
    setBusy(true)
    try {
      const data = await api(`/lezioni/${lessonId}/quiz-finale/`, {
        method: 'POST', body: JSON.stringify({ risposte: answers }),
      })
      setResult(data); onComplete?.(data)
    } finally { setBusy(false) }
  }

  const setAnswer = (value) => {
    setAnswers({ ...answers, [question.id]: value })
    setFeedback({ ...feedback, [question.id]: null })
  }

  return <section className="quiz-card" aria-labelledby={`quiz-h-${quiz.id}`}>
    <div className={`quiz-banner ${isFinal ? 'final' : 'guided'}`} role="note">
      {isFinal
        ? 'Quiz finale — determina il tuo punteggio.'
        : 'Esercizio guidato — non fa punteggio, esplora liberamente.'}
    </div>
    <div className="quiz-top">
      <h2 id={`quiz-h-${quiz.id}`}>{quiz.titolo}</h2>
      <b>{index + 1}/{total}</b>
    </div>
    <div className="meter" role="progressbar" aria-valuenow={index + 1} aria-valuemin={1} aria-valuemax={total}>
      <i style={{ '--pct': ((index + 1) / total) * 100 }} />
    </div>
    <h3 ref={questionHeadingRef} tabIndex={-1}>{question.testo}</h3>
    {question.tipo === 'scelta_multipla'
      ? <div className="options" role="radiogroup" aria-label="Opzioni">
          {question.opzioni.map(option => (
            <button
              key={option}
              role="radio"
              aria-checked={answer === option}
              className={answer === option ? 'selected' : ''}
              onClick={() => setAnswer(option)}
              type="button"
            >{option}</button>
          ))}
        </div>
      : <input
          className="completion"
          value={answer}
          placeholder="Scrivi la risposta…"
          onChange={e => setAnswer(e.target.value)}
        />}
    {checked && <div role="status" aria-live="polite" className={`feedback ${checked.corretta ? 'correct' : 'incorrect'}`}>
      <b>{checked.corretta ? 'Corretto!' : `Risposta corretta: ${checked.risposta_corretta}`}</b>
      <p>{checked.spiegazione}</p>
    </div>}
    <div className="quiz-actions">
      <button type="button" className="secondary" disabled={!answer || busy} onClick={verify}>Verifica</button>
      {checked && index < total - 1 && (
        <button type="button" className="primary" onClick={() => setIndex(index + 1)}>Continua →</button>
      )}
      {checked && index === total - 1 && isFinal && (
        <button type="button" className="primary" disabled={busy} onClick={finish}>Calcola punteggio</button>
      )}
      {checked && index === total - 1 && !isFinal && (
        <button type="button" className="primary" onClick={() => onComplete?.()}>Termina</button>
      )}
    </div>
  </section>
}
