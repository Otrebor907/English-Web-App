import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { Link, Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom'
import { api } from './api'

const AuthContext = createContext(null)
const AREA = {
  GRA: { label: 'Grammatica', icon: 'Aa', className: 'grammar' },
  VOC: { label: 'Vocabolario', icon: 'Ab', className: 'vocabulary' },
  COM: { label: 'Comunicazione', icon: 'Hi', className: 'communication' },
}
const STATUS_LABELS = {
  bloccata: 'Bloccata',
  disponibile: 'Disponibile',
  in_corso: 'In corso',
  completata: 'Completata',
  in_preparazione: 'In preparazione',
}

function AuthProvider({ children }) {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem('user') || 'null'))
  const authenticate = (payload) => {
    localStorage.setItem('token', payload.token)
    localStorage.setItem('user', JSON.stringify(payload.utente))
    setUser(payload.utente)
  }
  const logout = () => { localStorage.clear(); setUser(null) }
  return <AuthContext.Provider value={{ user, authenticate, logout }}>{children}</AuthContext.Provider>
}

function Layout({ children }) {
  const { user, logout } = useContext(AuthContext)
  return <>
    <a className="skip-link" href="#main-content">Vai al contenuto</a>
    <header className="topbar">
      <Link className="brand" to="/percorso"><span>PC</span> Prima conversazione</Link>
      {user && <nav aria-label="Navigazione principale">
        <Link to="/percorso">Percorso</Link>
        <Link to="/progressi">Progressi</Link>
        {user.is_staff && <Link to="/contenuti-da-completare">Contenuti</Link>}
        <Link to="/profilo">Profilo</Link>
        <button type="button" className="link-button" onClick={logout}>Esci</button>
      </nav>}
    </header>
    <main id="main-content">{children}</main>
    <footer>Un passo alla volta, fino alla tua prima conversazione.</footer>
  </>
}

function Protected({ children }) {
  const { user } = useContext(AuthContext)
  return user ? children : <Navigate to="/login" replace />
}

function AuthPage({ register = false }) {
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const { authenticate } = useContext(AuthContext)
  const navigate = useNavigate()
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError('')
    try {
      authenticate(await api(`/auth/${register ? 'registrati' : 'login'}/`, { method: 'POST', body: JSON.stringify(form) }))
      navigate('/percorso')
    } catch (err) {
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
      <label>Email<input type="email" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></label>
      <label>Password<input type="password" required minLength="8" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /></label>
      {error && <div className="alert" role="alert" aria-live="assertive">{error}</div>}
      <button className="primary" disabled={busy}>{busy ? 'Attendi…' : register ? 'Crea account' : 'Accedi'}</button>
      <small>{register ? 'Hai già un account?' : 'Non hai un account?'} <Link to={register ? '/login' : '/registrati'}>{register ? 'Accedi' : 'Registrati'}</Link></small>
    </form>
  </div>
}

function useLoad(loader, dependencies = []) {
  const [state, setState] = useState({ loading: true, data: null, error: '' })
  useEffect(() => {
    let active = true
    setState(s => ({ ...s, loading: true }))
    loader().then(data => active && setState({ loading: false, data, error: '' }))
          .catch(error => active && setState({ loading: false, data: null, error: error.message }))
    return () => { active = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies)
  return state
}

function StatusPill({ status }) {
  return <span className={`status ${status}`}>{STATUS_LABELS[status] || status}</span>
}

/**
 * Componente riutilizzabile ❌ → ✅ → perché.
 * Accessibile: usa una list semantica per le tre righe e aria-label sulle icone.
 * Riutilizzabile in ogni sezione di lezione ed esercizio guidato.
 */
export function ErrorBox({ wrong, right, why, className = '' }) {
  return <aside className={`error-box ${className}`} aria-label="Errore tipico degli italiani">
    <ul>
      <li className="error-row">
        <span className="error-icon wrong" aria-hidden="true">✕</span>
        <span className="sr-only">Sbagliato:</span>
        <p>{wrong}</p>
      </li>
      <li className="error-row">
        <span className="error-icon right" aria-hidden="true">✓</span>
        <span className="sr-only">Corretto:</span>
        <p>{right}</p>
      </li>
    </ul>
    <div className="why">
      <b>Perché</b>
      <p>{why}</p>
    </div>
  </aside>
}

function Section({ section }) {
  const content = section.contenuto || {}
  if (section.formato_web === 'errore_box') {
    return <ErrorBox wrong={content.errato} right={content.corretto} why={content.perche} />
  }
  if (section.formato_web === 'lista') {
    return <div className="content-section">
      <span className="section-label">{section.tipo_sezione}</span>
      <h2>{content.titolo || section.tipo_sezione}</h2>
      <ul>{(content.elementi || []).map((item, i) => <li key={i}>{item}</li>)}</ul>
    </div>
  }
  const body = content.testo
  return <div className="content-section">
    <span className="section-label">{section.tipo_sezione}</span>
    <h2>{content.titolo || section.tipo_sezione}</h2>
    {body && <p>{body}</p>}
    {content.esempio && <blockquote>
      <strong>{content.esempio}</strong>
      {content.traduzione && <small>{content.traduzione}</small>}
    </blockquote>}
  </div>
}

function SectionCarousel({ sezioni, onFinished }) {
  const [index, setIndex] = useState(0)
  const total = sezioni.length
  const headingRef = useRef(null)
  useEffect(() => {
    if (headingRef.current) headingRef.current.focus()
  }, [index])
  const section = sezioni[index]
  const isLast = index === total - 1
  return <div className="section-carousel" aria-label="Sezioni della lezione">
    <div className="section-progress" role="group" aria-label="Avanzamento sezioni">
      <div className="section-progress-meta">
        <span>Sezione <b>{index + 1}</b> di {total}</span>
        <span aria-hidden="true">{Math.round(((index + 1) / total) * 100)}%</span>
      </div>
      <div className="meter" role="progressbar" aria-valuenow={index + 1} aria-valuemin={1} aria-valuemax={total}>
        <i style={{ width: `${((index + 1) / total) * 100}%` }} />
      </div>
    </div>
    <div className="section-wrap" ref={headingRef} tabIndex={-1} aria-live="polite">
      <Section section={section} />
    </div>
    <div className="section-nav">
      <button type="button" className="secondary" onClick={() => setIndex(i => Math.max(0, i - 1))} disabled={index === 0}>← Precedente</button>
      <div className="section-dots" aria-hidden="true">
        {sezioni.map((_, i) => <span key={i} className={i === index ? 'dot active' : i < index ? 'dot done' : 'dot'} />)}
      </div>
      {!isLast && <button type="button" className="primary" onClick={() => setIndex(i => Math.min(total - 1, i + 1))}>Successiva →</button>}
      {isLast && <button type="button" className="primary" onClick={onFinished}>Vai agli esercizi →</button>}
    </div>
  </div>
}

function QuizView({ quiz, lessonId, onComplete }) {
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
    return <section className="quiz-result" aria-live="polite">
      <span aria-hidden="true">{result.superato ? '✓' : '↻'}</span>
      <h2>{result.punteggio}%</h2>
      <p>{result.superato ? 'Quiz superato! La lezione è completata.' : 'Riprova: serve almeno il 70%.'}</p>
      <small>Miglior punteggio: {result.miglior_punteggio}%</small>
    </section>
  }

  const answer = answers[question.id] || ''
  const checked = feedback[question.id]

  const verify = async () => {
    setBusy(true)
    try {
      const data = await api(`/lezioni/${lessonId}/quesiti/${question.id}/verifica/`, {
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
      <div>
        <span className="eyebrow">{isFinal ? 'QUIZ FINALE' : 'ESERCIZIO GUIDATO'}</span>
        <h2 id={`quiz-h-${quiz.id}`}>{quiz.titolo}</h2>
      </div>
      <b>{index + 1}/{total}</b>
    </div>
    <div className="meter" role="progressbar" aria-valuenow={index + 1} aria-valuemin={1} aria-valuemax={total}>
      <i style={{ width: `${((index + 1) / total) * 100}%` }} />
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

function InPreparationLesson({ lesson }) {
  const area = AREA[lesson.area] || AREA.GRA
  return <div className={`lesson-page ${area.className}`}>
    <div className="lesson-hero">
      <Link className="back" to="/percorso">← Percorso</Link>
      <span className="eyebrow">{area.label} · {lesson.livello}</span>
      <h1>{lesson.nome}</h1>
      <p>{lesson.descrizione}</p>
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
        <Link className="primary" to="/percorso">Torna al percorso</Link>
      </div>
    </div>
  </div>
}

function PathPage() {
  const { loading, data: lessons, error } = useLoad(() => api('/percorso/'))
  if (loading) return <Loader />
  if (error) return <ErrorState message={error} />
  const complete = lessons.filter(item => item.stato === 'completata').length
  const publishable = lessons.filter(item => !item.in_preparazione).length
  return <div className="page">
    <div className="page-heading">
      <div>
        <span className="eyebrow">IL TUO PERCORSO</span>
        <h1>Impara. Prova. Parla.</h1>
        <p>Ogni lezione prepara la successiva. Completa i prerequisiti per avanzare.</p>
      </div>
      <div className="progress-ring" role="img" aria-label={`${complete} lezioni completate su ${publishable}`}>
        <strong>{complete}/{publishable}</strong><span>lezioni</span>
      </div>
    </div>
    <ul className="lesson-list" aria-label="Elenco lezioni">
      {lessons.map((lesson, index) => {
        const area = AREA[lesson.area] || AREA.GRA
        const inPrep = lesson.in_preparazione
        const locked = lesson.stato === 'bloccata'
        const cardClass = `lesson-card ${locked ? 'locked' : ''} ${inPrep ? 'in-prep' : ''}`.trim()
        return <li key={lesson.id}>
          <article className={cardClass} aria-labelledby={`lc-${lesson.id}`}>
            <div className={`area-icon ${area.className}`} aria-hidden="true">
              {inPrep ? '…' : locked ? '⌁' : area.icon}
            </div>
            <div className="lesson-order" aria-hidden="true">{String(index + 1).padStart(2, '0')}</div>
            <div className="lesson-main">
              <div className="lesson-meta">
                <span>{area.label}</span>
                <span>{lesson.livello}</span>
                <span>{lesson.priorita}</span>
                <span>{lesson.durata_min} min</span>
              </div>
              <h2 id={`lc-${lesson.id}`}>{lesson.nome}</h2>
              <p>{lesson.descrizione}</p>
              {locked && !inPrep && (
                <p className="requirements"><b>Prima completa:</b> {lesson.prerequisiti_mancanti.map(x => x.nome).join(', ')}</p>
              )}
              {inPrep && (
                <p className="in-prep-note">Struttura editoriale definita, contenuti in arrivo.</p>
              )}
            </div>
            <div className="lesson-action">
              <StatusPill status={lesson.stato} />
              {!locked && !inPrep && (
                <Link className="arrow" aria-label={`Apri ${lesson.nome}`} to={`/lezioni/${lesson.id}`}>→</Link>
              )}
              {inPrep && (
                <Link className="arrow prep" aria-label={`Apri anteprima di ${lesson.nome}`} to={`/lezioni/${lesson.id}`}>i</Link>
              )}
            </div>
          </article>
        </li>
      })}
    </ul>
  </div>
}

function LessonPage() {
  const { id } = useParams()
  const { loading, data: lesson, error } = useLoad(() => api(`/lezioni/${id}/`), [id])
  const [phase, setPhase] = useState('sections')
  const [quizIndex, setQuizIndex] = useState(-1)
  const quizRef = useRef(null)

  const goToQuiz = useCallback(() => {
    setPhase('quiz')
    setTimeout(() => quizRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 20)
  }, [])

  useEffect(() => {
    if (lesson && !lesson.in_preparazione) {
      api(`/lezioni/${id}/inizia/`, { method: 'POST' }).catch(() => {})
    }
  }, [id, lesson])

  if (loading) return <Loader />
  if (error) return <ErrorState message={error} />
  if (lesson.in_preparazione) return <InPreparationLesson lesson={lesson} />

  const area = AREA[lesson.area] || AREA.GRA
  const hasSections = lesson.sezioni?.length > 0
  const hasQuiz = lesson.quiz?.length > 0

  return <div className={`lesson-page ${area.className}`}>
    <div className="lesson-hero">
      <Link className="back" to="/percorso">← Percorso</Link>
      <span className="eyebrow">{area.label} · {lesson.livello}</span>
      <h1>{lesson.nome}</h1>
      <p>{lesson.obiettivo_didattico}</p>
      <div className="hero-meta" aria-label="Dettagli lezione">
        <span>{lesson.durata_min} min</span>
        {lesson.priorita && <span>Priorità {lesson.priorita}</span>}
        {lesson.difficolta && <span>Difficoltà {lesson.difficolta}</span>}
      </div>
    </div>
    <div className="lesson-content">
      {hasSections && phase === 'sections' && (
        <SectionCarousel sezioni={lesson.sezioni} onFinished={goToQuiz} />
      )}
      {phase === 'quiz' && (
        <div ref={quizRef}>
          {!hasQuiz && (
            <section className="quiz-card empty">
              <span className="eyebrow">ESERCIZI</span>
              <h2>Quiz in preparazione</h2>
              <p>Le esercitazioni per questa lezione non sono ancora disponibili.</p>
              <button type="button" className="secondary" onClick={() => setPhase('sections')}>← Torna alle sezioni</button>
            </section>
          )}
          {hasQuiz && (
            <div className="quiz-launch" role="group" aria-label="Esercitazioni disponibili">
              <h2>È il momento di provare</h2>
              <p>Inizia dall'esercizio guidato, poi affronta il quiz finale.</p>
              <div className="quiz-launch-buttons">
                {lesson.quiz.map((quiz, i) => (
                  <button
                    key={quiz.id}
                    type="button"
                    className={quiz.modalita === 'finale' ? 'primary' : 'secondary'}
                    onClick={() => setQuizIndex(i)}
                    aria-pressed={quizIndex === i}
                  >{quiz.titolo}</button>
                ))}
              </div>
            </div>
          )}
          {quizIndex >= 0 && hasQuiz && (
            <QuizView
              quiz={lesson.quiz[quizIndex]}
              lessonId={id}
              onComplete={() => quizIndex < lesson.quiz.length - 1 && setQuizIndex(quizIndex + 1)}
            />
          )}
        </div>
      )}
    </div>
  </div>
}

function ProgressPage() {
  const { loading, data, error } = useLoad(() => api('/progressi/'))
  if (loading) return <Loader />
  if (error) return <ErrorState message={error} />
  return <div className="page narrow">
    <span className="eyebrow">I TUOI RISULTATI</span>
    <h1>Progressi</h1>
    {data.length === 0
      ? <div className="empty">Non hai ancora iniziato una lezione. <Link to="/percorso">Vai al percorso</Link>.</div>
      : <ul className="progress-list" aria-label="Elenco progressi">
          {data.map(item => <li key={item.lezione_id}><article>
            <div><h3>{item.lezione_nome}</h3><StatusPill status={item.stato} /></div>
            <strong>{item.punteggio}%</strong>
          </article></li>)}
        </ul>}
  </div>
}

function ProfilePage() {
  const { user } = useContext(AuthContext)
  return <div className="page narrow">
    <span className="eyebrow">IL TUO ACCOUNT</span>
    <h1>Profilo</h1>
    <div className="profile-card">
      <div className="avatar" aria-hidden="true">{user.email[0].toUpperCase()}</div>
      <div>
        <small>Email</small>
        <h2>{user.email}</h2>
        <p>Iscritto dal {new Date(user.creato_il).toLocaleDateString('it-IT')}</p>
      </div>
    </div>
  </div>
}

function ContentGapsPage() {
  const { user } = useContext(AuthContext)
  const { loading, data, error } = useLoad(() => api('/admin/contenuti-mancanti/'))
  if (!user.is_staff) return <Navigate to="/percorso" replace />
  if (loading) return <Loader />
  if (error) return <ErrorState message={error} />
  return <div className="page">
    <span className="eyebrow">CONTROLLO EDITORIALE</span>
    <h1>Contenuti da completare</h1>
    <div className="summary-grid">
      <div><strong>{data.riepilogo.lezioni_mvp}</strong><span>lezioni MVP</span></div>
      <div><strong>{data.riepilogo.sezioni_todo}</strong><span>sezioni TODO</span></div>
      <div><strong>{data.riepilogo.quiz_finali_mancanti}</strong><span>quiz finali mancanti</span></div>
    </div>
    <ul className="gap-list" aria-label="Lezioni con contenuti mancanti">
      {data.lezioni.map(lesson => <li key={lesson.id}><article>
        <div>
          <span className="lesson-meta">{lesson.area} · {lesson.priorita} · ordine {lesson.ordine_mvp}</span>
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

const Loader = () => <div className="loader" role="status" aria-live="polite">Caricamento…</div>
const ErrorState = ({ message }) => <div className="error-state">
  <h2>Qualcosa non ha funzionato</h2>
  <p>{message}</p>
  <Link to="/percorso">Torna al percorso</Link>
</div>

export default function App() {
  return <AuthProvider><Layout><Routes>
    <Route path="/login" element={<AuthPage />} />
    <Route path="/registrati" element={<AuthPage register />} />
    <Route path="/percorso" element={<Protected><PathPage /></Protected>} />
    <Route path="/lezioni/:id" element={<Protected><LessonPage /></Protected>} />
    <Route path="/progressi" element={<Protected><ProgressPage /></Protected>} />
    <Route path="/profilo" element={<Protected><ProfilePage /></Protected>} />
    <Route path="/contenuti-da-completare" element={<Protected><ContentGapsPage /></Protected>} />
    <Route path="*" element={<Navigate to="/percorso" replace />} />
  </Routes></Layout></AuthProvider>
}
