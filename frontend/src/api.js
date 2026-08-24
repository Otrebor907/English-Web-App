// Indirizzo base del backend Django (es. http://localhost:8000/api).
// In produzione VITE_API_URL è impostata a build-time; in sviluppo si deduce
// dall'host corrente, assumendo che Django giri sulla porta 8000.
const API_URL = import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.hostname}:8000/api`

// Unico punto da cui il frontend parla col backend: OGNI fetch dell'app passa da qui,
// così autenticazione e gestione errori sono scritte una sola volta.
export async function api(path, options = {}) {
  // Il "pass" di sessione non è un cookie: è una stringa (token) salvata dal browser
  // in localStorage dopo il login. Va riletta e rimandata ad ogni richiesta.
  const token = localStorage.getItem('token')
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      // Se esiste un token lo mandiamo nell'header Authorization: è così che Django
      // REST Framework (TokenAuthentication) riconosce "chi sta chiamando".
      // Se non c'è token (utente non loggato), l'header non viene aggiunto affatto.
      ...(token ? { Authorization: `Token ${token}` } : {}),
      ...options.headers,
    },
  })
  // Il corpo della risposta è sempre JSON; .catch(() => ({})) evita un crash
  // se il corpo è vuoto (es. risposte 204 No Content).
  const data = await response.json().catch(() => ({}))
  // response.ok è false per status 4xx/5xx (es. 400 password errata, 401 non autenticato).
  // Trasformiamo l'errore HTTP in un'eccezione JS con .data allegato, così i componenti
  // (es. AuthPage) possono leggere i messaggi di errore campo-per-campo restituiti da Django.
  if (!response.ok) throw Object.assign(new Error(data.detail || 'Si è verificato un errore'), { status: response.status, data })
  return data
}
