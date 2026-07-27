import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { Link, Navigate, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api } from './api'

const AuthContext = createContext(null)
const AREA = {
  GRA: { label: 'Grammatica', icon: 'Aa', className: 'grammar' },
  VOC: { label: 'Vocabolario', icon: 'Ab', className: 'vocabulary' },
  COM: { label: 'Comunicazione', icon: 'Hi', className: 'communication' },
}
const STATUS_LABELS = {
  disponibile: 'Non iniziata',
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
  const updateUser = (patch) => {
    setUser(current => {
      const next = { ...current, ...patch }
      localStorage.setItem('user', JSON.stringify(next))
      return next
    })
  }
  const updateToken = (token) => localStorage.setItem('token', token)
  const logout = () => { localStorage.clear(); setUser(null) }
  return <AuthContext.Provider value={{ user, authenticate, updateUser, updateToken, logout }}>{children}</AuthContext.Provider>
}

const NO_SIDEBAR_ROUTES = ['/', '/login', '/registrati']

function Layout({ children }) {
  const { user, logout } = useContext(AuthContext)
  const location = useLocation()
  const showSidebar = !NO_SIDEBAR_ROUTES.includes(location.pathname)
  return <>
    <a className="skip-link" href="#main-content">Vai al contenuto</a>
    <header className="topbar">
      <Link className="brand" to="/"><span className="brand-mark" aria-hidden="true">PC</span> Prima conversazione</Link>
      <nav aria-label="Navigazione principale">
        <Link to="/">Home</Link>
        <Link to="/lezioni">Lezioni</Link>
        {user && <Link to="/progressi">Progressi</Link>}
        {user?.is_staff && <Link to="/contenuti-da-completare">Contenuti</Link>}
        {user && <Link to="/profilo">Profilo</Link>}
        {user
          ? <button type="button" className="link-button" onClick={logout}>Esci</button>
          : <>
            <Link to="/login">Accedi</Link>
            <Link className="nav-cta" to="/registrati">Registrati</Link>
          </>}
      </nav>
    </header>
    <div className={showSidebar ? 'app-shell with-sidebar' : 'app-shell'}>
      {showSidebar && <LessonSidebar />}
      <main id="main-content">{children}</main>
    </div>
    <footer>Un passo alla volta, fino alla tua prima conversazione.</footer>
  </>
}

/** Raggruppa una lista di lezioni (già ordinate per ordine_percorso) per categoria,
 *  preservando l'ordine di prima comparsa. Ritorna [{ categoria, items }]. */
function groupByCategoria(lessons) {
  const groups = new Map()
  for (const lesson of lessons) {
    const key = lesson.categoria || 'Altro'
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(lesson)
  }
  return [...groups.entries()].map(([categoria, items]) => ({ categoria, items }))
}

/** Gerarchia a tre livelli Macro argomento → Categoria → Lezioni, usata quando
 *  nessuna area è selezionata (altrimenti l'area è già implicita nel filtro attivo). */
function groupByAreaAndCategoria(lessons) {
  return Object.entries(AREA)
    .map(([code, info]) => ({ code, info, items: lessons.filter(l => l.area === code) }))
    .filter(group => group.items.length > 0)
    .map(group => ({ ...group, categorie: groupByCategoria(group.items) }))
}

function LessonSidebar() {
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

function Protected({ children }) {
  const { user } = useContext(AuthContext)
  const location = useLocation()
  if (user) return children
  return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />
}

function HomePage() {
  const { user } = useContext(AuthContext)
  const { data: assigned } = useLoad(() => user ? api('/progressi/') : Promise.resolve(null), [Boolean(user)])
  return <div className="home">
    <section className="home-hero">
      <h1>Impara l'inglese, una lezione alla volta.</h1>
      <p>Esplora gratuitamente tutte le lezioni di grammatica, vocabolario e comunicazione. Registrati quando vuoi assegnarti le lezioni, svolgere gli esercizi e tenere traccia dei tuoi progressi.</p>
      <div className="home-cta">
        <Link className="primary" to="/lezioni">Esplora le lezioni</Link>
        {user
          ? <Link className="secondary" to="/progressi">Vai ai tuoi progressi</Link>
          : <Link className="secondary" to="/registrati">Registrati gratuitamente</Link>}
      </div>
      {user && assigned?.length > 0 && (
        <p className="home-summary">
          Hai {assigned.length} {assigned.length === 1 ? 'lezione assegnata' : 'lezioni assegnate'} al tuo percorso
          {assigned.some(item => item.stato === 'completata') && <> — {assigned.filter(item => item.stato === 'completata').length} completate</>}.
        </p>
      )}
    </section>
    <section className="home-open">
      <h2>Le lezioni sono aperte a tutti.</h2>
      <p>Non serve un account per studiare. Consulta liberamente spiegazioni, esempi ed errori tipici, scegli l'argomento che ti interessa e impara seguendo il tuo ritmo.</p>
    </section>
    <section className="home-modes">
      <div className="home-mode-card">
        <h3>Studia senza registrarti</h3>
        <ul>
          <li>Consulta tutte le lezioni</li>
          <li>Leggi regole ed esempi</li>
          <li>Naviga liberamente tra i livelli</li>
          <li>Nessun percorso obbligatorio</li>
        </ul>
      </div>
      <div className="home-mode-card featured">
        <h3>Registrati e segui i progressi</h3>
        <ul>
          <li>Assegna le lezioni al tuo percorso</li>
          <li>Svolgi gli esercizi</li>
          <li>Ricevi correzioni e spiegazioni</li>
          <li>Salva risultati e avanzamento</li>
          <li>Riprendi da dove avevi interrotto</li>
        </ul>
        {!user && <Link className="primary" to="/registrati">Crea il tuo account</Link>}
      </div>
    </section>
    <section className="home-areas">
      <h2>Come è organizzato il catalogo</h2>
      <div className="home-area-grid">
        <article className="home-area-card grammar">
          <span className="area-icon grammar" aria-hidden="true">Aa</span>
          <h3>Grammatica</h3>
          <p>Le regole spiegate con esempi e con gli errori tipici di chi parla italiano — non da imparare a memoria.</p>
        </article>
        <article className="home-area-card vocabulary">
          <span className="area-icon vocabulary" aria-hidden="true">Ab</span>
          <h3>Vocabolario</h3>
          <p>Le parole e le espressioni che servono davvero per farsi capire in una conversazione reale.</p>
        </article>
        <article className="home-area-card communication">
          <span className="area-icon communication" aria-hidden="true">Hi</span>
          <h3>Comunicazione</h3>
          <p>Situazioni concrete — dal presentarti al parlare al telefono — con le frasi da usare.</p>
        </article>
      </div>
    </section>
    <section className="home-how">
      <h2>Come funziona una lezione</h2>
      <ol className="home-steps">
        <li><b>Leggi</b> — la spiegazione scorre come un testo continuo, senza dover cliccare avanti e indietro tra le regole.</li>
        <li><b>Esercitati</b> — in fondo alla lezione trovi l'esercizio guidato e il quiz finale, con la correzione spiegata (per chi ha un account).</li>
        <li><b>Tieni traccia</b> — il punteggio migliore resta salvato nei tuoi progressi, lezione per lezione.</li>
      </ol>
    </section>
  </div>
}

function AuthPage({ register = false }) {
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const { authenticate } = useContext(AuthContext)
  const navigate = useNavigate()
  const location = useLocation()
  const next = new URLSearchParams(location.search).get('next') || '/lezioni'
  const nextQuery = next !== '/lezioni' ? `?next=${encodeURIComponent(next)}` : ''
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError('')
    try {
      authenticate(await api(`/auth/${register ? 'registrati' : 'login'}/`, { method: 'POST', body: JSON.stringify(form) }))
      navigate(next)
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
      <small>{register ? 'Hai già un account?' : 'Non hai un account?'} <Link to={`${register ? '/login' : '/registrati'}${nextQuery}`}>{register ? 'Accedi' : 'Registrati'}</Link></small>
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

function useCountUp(target, duration = 1200) {
  const [value, setValue] = useState(target)
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { setValue(target); return }
    let raf
    const start = performance.now()
    setValue(0)
    const tick = (now) => {
      const p = Math.min(1, (now - start) / duration)
      setValue(Math.round((1 - Math.pow(1 - p, 3)) * target))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target])
  return value
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
    // Supporta sia il box singolo storico sia una lista di errori (content.errori).
    const errori = Array.isArray(content.errori) && content.errori.length
      ? content.errori
      : [{ errato: content.errato, corretto: content.corretto, perche: content.perche }]
    return <div className="content-section">
      {content.titolo && <><span className="section-label">{section.tipo_sezione}</span><h2>{content.titolo}</h2></>}
      {errori.map((e, i) => <ErrorBox key={i} wrong={e.errato} right={e.corretto} why={e.perche} />)}
    </div>
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

function SectionList({ sezioni }) {
  return <div className="section-list" aria-label="Contenuto della lezione">
    {sezioni.map((section, i) => <Section key={i} section={section} />)}
  </div>
}

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
    return <ResultCard result={result} />
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

function InPreparationLesson({ lesson }) {
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

function LessonCard({ lesson, index, user }) {
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

function LessonsPage() {
  const { user } = useContext(AuthContext)
  const { loading, data, error } = useLoad(() => api('/lezioni/indice/'))
  const [area, setArea] = useState('TUTTE')
  const [categoria, setCategoria] = useState('TUTTE')
  if (loading) return <Loader />
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
        <strong>{assignedCount}</strong><span>nel percorso</span>
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

function LessonPage() {
  const { id } = useParams()
  const { user } = useContext(AuthContext)
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
        {lesson.priorita && <span>Priorità {lesson.priorita}</span>}
        {lesson.difficolta && <span>Difficoltà {lesson.difficolta}</span>}
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

function ProgressPage() {
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

function ProfilePage() {
  const { user, updateUser, updateToken } = useContext(AuthContext)
  const [emailForm, setEmailForm] = useState({ email: user.email })
  const [emailState, setEmailState] = useState({ busy: false, error: '', success: false })
  const [passwordForm, setPasswordForm] = useState({ password_attuale: '', nuova_password: '' })
  const [passwordState, setPasswordState] = useState({ busy: false, error: '', success: false })

  const submitEmail = async (event) => {
    event.preventDefault()
    setEmailState({ busy: true, error: '', success: false })
    try {
      const data = await api('/profilo/', { method: 'PATCH', body: JSON.stringify({ email: emailForm.email }) })
      updateUser({ email: data.email })
      setEmailState({ busy: false, error: '', success: true })
    } catch (err) {
      setEmailState({ busy: false, error: err.data?.email?.[0] || err.message, success: false })
    }
  }

  const submitPassword = async (event) => {
    event.preventDefault()
    setPasswordState({ busy: true, error: '', success: false })
    try {
      const data = await api('/auth/password/', { method: 'POST', body: JSON.stringify(passwordForm) })
      updateToken(data.token)
      setPasswordForm({ password_attuale: '', nuova_password: '' })
      setPasswordState({ busy: false, error: '', success: true })
    } catch (err) {
      setPasswordState({
        busy: false,
        error: err.data?.password_attuale?.[0] || err.data?.nuova_password?.[0] || err.message,
        success: false,
      })
    }
  }

  return <div className="page narrow">
    <h1>Profilo</h1>
    <div className="profile-card">
      <div className="avatar" aria-hidden="true">{user.email[0].toUpperCase()}</div>
      <div>
        <small>Email</small>
        <h2>{user.email}</h2>
        <p>Iscritto dal {new Date(user.creato_il).toLocaleDateString('it-IT')}</p>
      </div>
    </div>

    <form className="settings-card" onSubmit={submitEmail}>
      <h2>Cambia email</h2>
      <p>Aggiorna l'indirizzo collegato al tuo account.</p>
      <label>Nuova email
        <input
          type="email" required value={emailForm.email}
          onChange={e => { setEmailForm({ email: e.target.value }); setEmailState(s => ({ ...s, error: '', success: false })) }}
          aria-describedby="email-helper" aria-invalid={Boolean(emailState.error)}
        />
      </label>
      <div id="email-helper" className="field-helper" aria-live="polite">
        {emailState.error && <span className="field-error" role="alert">{emailState.error}</span>}
        {!emailState.error && emailState.success && <span className="field-success">✓ Email aggiornata.</span>}
      </div>
      <button className="primary" disabled={emailState.busy}>{emailState.busy ? 'Attendi…' : 'Salva email'}</button>
    </form>

    <form className="settings-card" onSubmit={submitPassword}>
      <h2>Cambia password</h2>
      <p>Scegli una nuova password di almeno 8 caratteri.</p>
      <label>Password attuale
        <input
          type="password" required value={passwordForm.password_attuale}
          onChange={e => { setPasswordForm({ ...passwordForm, password_attuale: e.target.value }); setPasswordState(s => ({ ...s, error: '', success: false })) }}
        />
      </label>
      <label>Nuova password
        <input
          type="password" required minLength="8" value={passwordForm.nuova_password}
          onChange={e => { setPasswordForm({ ...passwordForm, nuova_password: e.target.value }); setPasswordState(s => ({ ...s, error: '', success: false })) }}
          aria-describedby="password-helper" aria-invalid={Boolean(passwordState.error)}
        />
      </label>
      <div id="password-helper" className="field-helper" aria-live="polite">
        {passwordState.error && <span className="field-error" role="alert">{passwordState.error}</span>}
        {!passwordState.error && passwordState.success && <span className="field-success">✓ Password aggiornata.</span>}
      </div>
      <button className="primary" disabled={passwordState.busy}>{passwordState.busy ? 'Attendi…' : 'Aggiorna password'}</button>
    </form>
  </div>
}

function ContentGapsPage() {
  const { user } = useContext(AuthContext)
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
  <Link to="/lezioni">Torna alle lezioni</Link>
</div>

export default function App() {
  return <AuthProvider><Layout><Routes>
    <Route path="/" element={<HomePage />} />
    <Route path="/login" element={<AuthPage />} />
    <Route path="/registrati" element={<AuthPage register />} />
    <Route path="/lezioni" element={<LessonsPage />} />
    <Route path="/percorso" element={<Navigate to="/lezioni" replace />} />
    <Route path="/lezioni/:id" element={<LessonPage />} />
    <Route path="/progressi" element={<Protected><ProgressPage /></Protected>} />
    <Route path="/profilo" element={<Protected><ProfilePage /></Protected>} />
    <Route path="/contenuti-da-completare" element={<Protected><ContentGapsPage /></Protected>} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></Layout></AuthProvider>
}
