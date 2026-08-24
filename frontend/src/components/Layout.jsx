import { useLocation } from 'react-router-dom'
import Header from './Header'
import Footer from './Footer'
import LessonSidebar from './LessonSidebar'

// Le rotte in cui non serve mostrare la sidebar delle lezioni.
// Su Home, login e registrazione il layout resta più semplice.
const NO_SIDEBAR_ROUTES = ['/', '/login', '/registrati']

// Layout è il contenitore comune di tutte le pagine dell'app.
// Qui vengono renderizzati gli elementi fissi: header, eventuale sidebar e footer.
// Il contenuto variabile di ciascuna pagina viene passato tramite `children`.
export default function Layout({ children }) {
  //variazione di React Router che permette di leggere l'URL corrente (es. /lezioni/1)
  const location = useLocation()
  // NO_SIDEBAR_ROUTES è dentro /login e /registrati, quindi in quei casi non serve mostrare la sidebar.
  const showSidebar = !NO_SIDEBAR_ROUTES.includes(location.pathname)

  return <>
    {/* Link accessibile per saltare direttamente al contenuto principale. */}
    <a className="skip-link" href="#main-content">Vai al contenuto</a>

    {/* Header fisso presente su tutte le pagine. */}
    <Header />

    {/* Contenitore principale: include la sidebar solo quando serve. */}
    <div className={showSidebar ? 'app-shell with-sidebar' : 'app-shell'}>
      {showSidebar && <LessonSidebar />}
      <main id="main-content">{children}</main>
    </div>

    {/* Footer fisso presente in fondo a ogni pagina. */}
    <Footer />
  </>
}
