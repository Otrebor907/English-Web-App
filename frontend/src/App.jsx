import { createContext, useContext, useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api } from './api'

const AuthContext = createContext(null)
const AREA = {
  GRA: { label: 'Grammatica', icon: 'Aa', className: 'grammar' },
  VOC: { label: 'Vocabolario', icon: 'Ab', className: 'vocabulary' },
  COM: { label: 'Comunicazione', icon: 'Hi', className: 'communication' },
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
      {user && <nav aria-label="Navigazione principale"><Link to="/percorso">Percorso</Link><Link to="/progressi">Progressi</Link>{user.is_staff && <Link to="/contenuti-da-completare">Contenuti</Link>}<Link to="/profilo">Profilo</Link><button type="button" className="link-button" onClick={logout}>Esci</button></nav>}
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
    try { authenticate(await api(`/auth/${register ? 'registrati' : 'login'}/`, { method: 'POST', body: JSON.stringify(form) })); navigate('/percorso') }
    catch (err) { setError(err.data?.email?.[0] || err.data?.password?.[0] || err.message) }
    finally { setBusy(false) }
  }
  return <div className="auth-shell"><section className="auth-copy"><span className="eyebrow">INGLESE, SENZA ANSIA</span><h1>Dalle basi alla tua <em>prima conversazione.</em></h1><p>Un percorso chiaro, progettato intorno agli errori che facciamo più spesso noi italiani.</p></section>
    <form className="auth-card" onSubmit={submit}><h2>{register ? 'Crea il tuo profilo' : 'Bentornato'}</h2><p>{register ? 'Inizia gratuitamente il percorso.' : 'Riprendi da dove eri rimasto.'}</p>
      <label>Email<input type="email" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></label>
      <label>Password<input type="password" required minLength="8" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /></label>
      {error && <div className="alert" role="alert" aria-live="assertive">{error}</div>}<button className="primary" disabled={busy}>{busy ? 'Attendi…' : register ? 'Crea account' : 'Accedi'}</button>
      <small>{register ? 'Hai già un account?' : 'Non hai un account?'} <Link to={register ? '/login' : '/registrati'}>{register ? 'Accedi' : 'Registrati'}</Link></small>
    </form></div>
}

function useLoad(loader, dependencies = []) {
  const [state, setState] = useState({ loading: true, data: null, error: '' })
  useEffect(() => { let active = true; setState(s => ({ ...s, loading: true })); loader().then(data => active && setState({ loading: false, data, error: '' })).catch(error => active && setState({ loading: false, data: null, error: error.message })); return () => { active = false } }, dependencies)
  return state
}

function StatusPill({ status }) {
  const labels = { bloccata: 'Bloccata', disponibile: 'Disponibile', in_corso: 'In corso', completata: 'Completata' }
  return <span className={`status ${status}`}>{labels[status]}</span>
}

function PathPage() {
  const { loading, data: lessons, error } = useLoad(() => api('/percorso/'))
  if (loading) return <Loader />
  if (error) return <ErrorState message={error} />
  const complete = lessons.filter(item => item.stato === 'completata').length
  return <div className="page"><div className="page-heading"><div><span className="eyebrow">IL TUO PERCORSO</span><h1>Impara. Prova. Parla.</h1><p>Ogni lezione prepara la successiva. Completa i prerequisiti per avanzare.</p></div><div className="progress-ring"><strong>{complete}/{lessons.length}</strong><span>lezioni</span></div></div>
    <div className="lesson-list">{lessons.map((lesson, index) => { const area = AREA[lesson.area] || AREA.GRA; const locked = lesson.stato === 'bloccata'; return <article className={`lesson-card ${locked ? 'locked' : ''}`} key={lesson.id}>
      <div className={`area-icon ${area.className}`}>{locked ? '⌁' : area.icon}</div><div className="lesson-order">{String(index + 1).padStart(2, '0')}</div><div className="lesson-main"><div className="lesson-meta"><span>{area.label}</span><span>{lesson.livello}</span><span>{lesson.priorita}</span><span>{lesson.durata_min} min</span></div><h2>{lesson.nome}</h2><p>{lesson.descrizione}</p>{locked && <p className="requirements"><b>Prima completa:</b> {lesson.prerequisiti_mancanti.map(x => x.nome).join(', ')}</p>}</div>
      <div className="lesson-action"><StatusPill status={lesson.stato} />{!locked && <Link className="arrow" aria-label={`Apri ${lesson.nome}`} to={`/lezioni/${lesson.id}`}>→</Link>}</div>
    </article> })}</div></div>
}

export function ErrorBox({ wrong, right, why }) {
  return <aside className="error-box"><div><span>✕</span><p>{wrong}</p></div><div><span>✓</span><p>{right}</p></div><div className="why"><b>Perché</b><p>{why}</p></div></aside>
}

function Section({ section }) {
  const content = section.contenuto || {}
  const body = content.testo || content.todo
  if (section.formato_web === 'errore_box') return <ErrorBox wrong={content.errato} right={content.corretto} why={content.perche} />
  if (section.formato_web === 'lista') return <section className="content-section"><h2>{content.titolo || section.tipo_sezione}</h2><ul>{(content.elementi || []).map((item, i) => <li key={i}>{item}</li>)}</ul></section>
  return <section className="content-section"><span className="section-label">{section.tipo_sezione}</span><h2>{content.titolo}</h2>{body && <p>{body}</p>}{content.esempio && <blockquote><strong>{content.esempio}</strong>{content.traduzione && <small>{content.traduzione}</small>}</blockquote>}</section>
}

function QuizView({ quiz, lessonId, onComplete }) {
  const [index, setIndex] = useState(0), [answers, setAnswers] = useState({}), [feedback, setFeedback] = useState({}), [result, setResult] = useState(null)
  const question = quiz.quesiti[index]
  if (!question) return null
  const answer = answers[question.id] || ''
  const verify = async () => { const data = await api(`/lezioni/${lessonId}/quesiti/${question.id}/verifica/`, { method: 'POST', body: JSON.stringify({ risposta: answer }) }); setFeedback({ ...feedback, [question.id]: data }) }
  const finish = async () => { const data = await api(`/lezioni/${lessonId}/quiz-finale/`, { method: 'POST', body: JSON.stringify({ risposte: answers }) }); setResult(data); onComplete?.(data) }
  if (result) return <div className="quiz-result"><span>{result.superato ? '✓' : '↻'}</span><h2>{result.punteggio}%</h2><p>{result.superato ? 'Quiz superato! La lezione è completata.' : 'Riprova: serve almeno il 70%.'}</p><small>Miglior punteggio: {result.miglior_punteggio}%</small></div>
  const checked = feedback[question.id]
  return <section className="quiz-card"><div className="quiz-top"><div><span className="eyebrow">{quiz.modalita === 'guidato' ? 'ESERCIZIO GUIDATO · NON FA PUNTEGGIO' : 'QUIZ FINALE'}</span><h2>{quiz.titolo}</h2></div><b>{index + 1}/{quiz.quesiti.length}</b></div><div className="meter"><i style={{ width: `${(index + 1) / quiz.quesiti.length * 100}%` }} /></div><h3>{question.testo}</h3>
    {question.tipo === 'scelta_multipla' ? <div className="options">{question.opzioni.map(option => <button className={answer === option ? 'selected' : ''} key={option} onClick={() => { setAnswers({ ...answers, [question.id]: option }); setFeedback({ ...feedback, [question.id]: null }) }}>{option}</button>)}</div> : <input className="completion" value={answer} placeholder="Scrivi la risposta…" onChange={e => { setAnswers({ ...answers, [question.id]: e.target.value }); setFeedback({ ...feedback, [question.id]: null }) }} />}
    {checked && <div role="status" aria-live="polite" className={`feedback ${checked.corretta ? 'correct' : 'incorrect'}`}><b>{checked.corretta ? 'Corretto!' : `Risposta corretta: ${checked.risposta_corretta}`}</b><p>{checked.spiegazione}</p></div>}
    <div className="quiz-actions"><button className="secondary" disabled={!answer} onClick={verify}>Verifica</button>{checked && index < quiz.quesiti.length - 1 && <button className="primary" onClick={() => setIndex(index + 1)}>Continua →</button>}{checked && index === quiz.quesiti.length - 1 && quiz.modalita === 'finale' && <button className="primary" onClick={finish}>Calcola punteggio</button>}{checked && index === quiz.quesiti.length - 1 && quiz.modalita === 'guidato' && <button className="primary" onClick={() => onComplete?.()}>Termina</button>}</div>
  </section>
}

function LessonPage() {
  const { id } = useParams(), navigate = useNavigate()
  const { loading, data: lesson, error } = useLoad(() => api(`/lezioni/${id}/`), [id])
  const [quizIndex, setQuizIndex] = useState(-1)
  useEffect(() => { api(`/lezioni/${id}/inizia/`, { method: 'POST' }).catch(() => {}) }, [id])
  if (loading) return <Loader />
  if (error) return <ErrorState message={error} />
  const area = AREA[lesson.area] || AREA.GRA
  return <div className={`lesson-page ${area.className}`}><div className="lesson-hero"><button className="back" onClick={() => navigate('/percorso')}>← Percorso</button><span className="eyebrow">{area.label} · {lesson.livello}</span><h1>{lesson.nome}</h1><p>{lesson.obiettivo_didattico}</p></div><div className="lesson-content">{lesson.sezioni.map(section => <Section key={section.ordine} section={section} />)}
    {lesson.quiz.length > 0 && <div className="quiz-launch"><h2>È il momento di provare</h2><p>Inizia dall'esercizio guidato, poi affronta il quiz finale.</p><div>{lesson.quiz.map((quiz, i) => <button className={quiz.modalita === 'finale' ? 'primary' : 'secondary'} onClick={() => setQuizIndex(i)} key={quiz.id}>{quiz.titolo}</button>)}</div></div>}
    {quizIndex >= 0 && <QuizView quiz={lesson.quiz[quizIndex]} lessonId={id} onComplete={() => quizIndex < lesson.quiz.length - 1 && setQuizIndex(quizIndex + 1)} />}
  </div></div>
}

function ProgressPage() {
  const { loading, data, error } = useLoad(() => api('/progressi/'))
  if (loading) return <Loader />; if (error) return <ErrorState message={error} />
  return <div className="page narrow"><span className="eyebrow">I TUOI RISULTATI</span><h1>Progressi</h1>{data.length === 0 ? <div className="empty">Non hai ancora iniziato una lezione. <Link to="/percorso">Vai al percorso</Link>.</div> : <div className="progress-list">{data.map(item => <article key={item.lezione_id}><div><h3>{item.lezione_nome}</h3><StatusPill status={item.stato} /></div><strong>{item.punteggio}%</strong></article>)}</div>}</div>
}

function ProfilePage() {
  const { user } = useContext(AuthContext)
  return <div className="page narrow"><span className="eyebrow">IL TUO ACCOUNT</span><h1>Profilo</h1><div className="profile-card"><div className="avatar">{user.email[0].toUpperCase()}</div><div><small>Email</small><h2>{user.email}</h2><p>Iscritto dal {new Date(user.creato_il).toLocaleDateString('it-IT')}</p></div></div></div>
}

function ContentGapsPage() {
  const { user } = useContext(AuthContext)
  const { loading, data, error } = useLoad(() => api('/admin/contenuti-mancanti/'))
  if (!user.is_staff) return <Navigate to="/percorso" replace />
  if (loading) return <Loader />; if (error) return <ErrorState message={error} />
  return <div className="page"><span className="eyebrow">CONTROLLO EDITORIALE</span><h1>Contenuti da completare</h1><div className="summary-grid"><div><strong>{data.riepilogo.lezioni_mvp}</strong><span>lezioni MVP</span></div><div><strong>{data.riepilogo.sezioni_todo}</strong><span>sezioni TODO</span></div><div><strong>{data.riepilogo.quiz_finali_mancanti}</strong><span>quiz finali mancanti</span></div></div>
    <div className="gap-list">{data.lezioni.map(lesson => <article key={lesson.id}><div><span className="lesson-meta">{lesson.area} · {lesson.priorita} · ordine {lesson.ordine_mvp}</span><h2>{lesson.nome}</h2><small>{lesson.id} · {lesson.stato_sorgente}</small></div><div><b>{lesson.sezioni_todo.length} sezioni TODO</b><span>{lesson.quiz_finale_mancante ? 'Quiz finale mancante' : 'Quiz finale presente'}</span></div></article>)}</div>
  </div>
}

const Loader = () => <div className="loader" role="status" aria-live="polite">Caricamento…</div>
const ErrorState = ({ message }) => <div className="error-state"><h2>Qualcosa non ha funzionato</h2><p>{message}</p><Link to="/percorso">Torna al percorso</Link></div>

export default function App() {
  return <AuthProvider><Layout><Routes>
    <Route path="/login" element={<AuthPage />} /><Route path="/registrati" element={<AuthPage register />} />
    <Route path="/percorso" element={<Protected><PathPage /></Protected>} /><Route path="/lezioni/:id" element={<Protected><LessonPage /></Protected>} />
    <Route path="/progressi" element={<Protected><ProgressPage /></Protected>} /><Route path="/profilo" element={<Protected><ProfilePage /></Protected>} />
    <Route path="/contenuti-da-completare" element={<Protected><ContentGapsPage /></Protected>} />
    <Route path="*" element={<Navigate to="/percorso" replace />} />
  </Routes></Layout></AuthProvider>
}
