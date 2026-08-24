import { createContext, useContext, useState } from 'react'

// AuthContext è il "contenitore globale" che dice a qualsiasi componente dell'app
// se c'è un utente loggato e come effettuare login/logout, senza dover passare
// queste informazioni manualmente componente per componente (prop drilling).
const AuthContext = createContext(null)

// Scorciatoia usata in tutti i componenti: invece di scrivere ogni volta
// useContext(AuthContext), si scrive useAuth(). Tenere l'accesso al context
// dietro un unico hook rende più facile un domani cambiarne l'implementazione.
export function useAuth() {
  return useContext(AuthContext)
}

/**
 * Componente che avvolge tutta l'app (vedi App.jsx) e gestisce lo stato di
 * autenticazione lato frontend.
 *
 * Punto chiave per capire "come fa la navbar a sapere se sei loggato":
 * `user` è lo stato React che ogni componente legge tramite useAuth().
 * Quando `user` è null, tutta l'app si comporta come "visitatore anonimo".
 */
export function AuthProvider({ children }) {
  // Stato iniziale: alla primissima apertura della pagina (refresh incluso) il
  // componente legge localStorage. Se in un login precedente avevamo salvato
  // l'utente, lo stato parte già "loggato" — per questo il login "resta" anche
  // dopo un refresh del browser, pur non essendoci una sessione lato server.
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem('user') || 'null'))

  // Chiamata dalla pagina Auth dopo che login/registrazione hanno avuto successo.
  // `payload` è esattamente la risposta JSON del backend: { token, utente }.
  const authenticate = (payload) => {
    // Il token va in localStorage perché serve ad api.js (frontend/src/api.js)
    // per autenticare le richieste future: senza salvarlo, si perderebbe al refresh.
    localStorage.setItem('token', payload.token)
    localStorage.setItem('user', JSON.stringify(payload.utente))
    // Aggiornare lo stato React (setUser) è ciò che fa ri-renderizzare la navbar,
    // mostrando subito Progressi/Profilo/Esci al posto di Accedi/Registrati.
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
  // Logout: azzerando localStorage e lo stato, l'app torna a comportarsi
  // come se nessuno avesse mai fatto login.
  const logout = () => { localStorage.clear(); setUser(null) }
  // Espone user + le funzioni a tutti i discendenti tramite il Context creato sopra.
  return <AuthContext.Provider value={{ user, authenticate, updateUser, updateToken, logout }}>{children}</AuthContext.Provider>
}
