import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'
import { useLoad } from '../hooks/useLoad'

// Pagina iniziale (rotta "/"). Presenta il progetto e, se l'utente è loggato,
// mostra un breve riepilogo delle lezioni assegnate al suo percorso.
export default function Home() {
  const { user } = useAuth()
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
      {/* se l'utente non è loggato mostrare frase*/}
      {user && assigned?.length === 0 && (
        <p className="home-summary">
          hai 0 lezioni assegnate al tuo percorso. Registrati per iniziare a seguire le lezioni.
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
