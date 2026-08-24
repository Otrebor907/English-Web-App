import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

// Wrapper usato nelle route riservate (es. /progressi, /profilo — vedi App.jsx).
// Se l'utente NON è loggato, invece di mostrare la pagina lo si rimanda al login,
// ricordando in ?next= la pagina che voleva vedere, per riportarcelo dopo l'accesso.
export default function Protected({ children }) {
  const { user } = useAuth()
  const location = useLocation()
  if (user) return children
  return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />
}
