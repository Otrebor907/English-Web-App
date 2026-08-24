import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Layout from './components/Layout'
import Protected from './components/Protected'
import Home from './pages/Home'
import Auth from './pages/Auth'
import Lessons from './pages/Lessons'
import Lesson from './pages/Lesson'
import Progress from './pages/Progress'
import Profile from './pages/Profile'
import ContentGaps from './pages/ContentGaps'

// Componente radice: monta AuthProvider (stato di login globale) attorno a Layout
// (navbar+footer fissi) attorno a Routes (react-router sceglie QUALE pagina
// disegnare in base all'URL del browser, senza mai ricaricare l'HTML).
//
// Questo file è ora una semplice "mappa": ogni riga associa un URL a una pagina
// di src/pages/. Per vedere cosa fa una pagina, si apre il file corrispondente.
export default function App() {
  return <AuthProvider><Layout><Routes>
    <Route path="/" element={<Home />} />
    {/* /login e /registrati usano lo stesso componente Auth: la prop
        `register` distingue le due modalità (vedi pages/Auth.jsx). */}
    <Route path="/login" element={<Auth />} />
    <Route path="/registrati" element={<Auth register />} />
    <Route path="/lezioni" element={<Lessons />} />
    <Route path="/percorso" element={<Navigate to="/lezioni" replace />} />
    <Route path="/lezioni/:id" element={<Lesson />} />
    <Route path="/progressi" element={<Protected><Progress /></Protected>} />
    <Route path="/profilo" element={<Protected><Profile /></Protected>} />
    <Route path="/contenuti-da-completare" element={<Protected><ContentGaps /></Protected>} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></Layout></AuthProvider>
}
