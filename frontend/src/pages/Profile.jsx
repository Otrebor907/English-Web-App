import { useState } from 'react'
import { api } from '../api'
import { useAuth } from '../context/AuthContext'

// Pagina profilo (rotta "/profilo", riservata ai loggati): permette di cambiare
// email e password. Ogni form ha il suo stato di busy/errore/successo indipendente.
export default function Profile() {
  const { user, updateUser, updateToken } = useAuth()
  
  // devo cambiare email
  const [emailForm, setEmailForm] = useState({ email: user.email })
  const [emailState, setEmailState] = useState({ busy: false, error: '', success: false })
  
  // devo cambiare nome 
  const [nameForm, setNameForm] = useState({ nome: user.nome, cognome: user.cognome })
  const [nameState, setNameState] = useState({ busy: false, error: '', success: false })
  
  // devo cambiare cognome
  const [cognomeForm, setCognomeForm] = useState({ cognome: user.cognome })
  const [cognomeState, setCognomeState] = useState({ busy: false, error: '', success: false })

  // devo cambiare password
  const [passwordForm, setPasswordForm] = useState({ password_attuale: '', nuova_password: '' })
  const [passwordState, setPasswordState] = useState({ busy: false, error: '', success: false })

  // Gestore dell'invio del form per cambiare l'email: fa PATCH a /api/profilo/ con la nuova email.
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

  // Gestore dell'invio del form per cambiare il nome e cognome: fa PATCH a /api/profilo/ con i nuovi dati.
  const submitName = async (event) => {
    event.preventDefault()
    setNameState({ busy: true, error: '', success: false })
    try {
      const data = await api('/profilo/', { method: 'PATCH', body: JSON.stringify({ nome: nameForm.nome, cognome: nameForm.cognome }) })
      updateUser({ nome: data.nome, cognome: data.cognome })
      setNameState({ busy: false, error: '', success: true })
    } catch (err) {
      setNameState({ busy: false, error: err.data?.nome?.[0] || err.data?.cognome?.[0] || err.message, success: false })
    }
  }

   // Gestore dell'invio del form per cambiare il cognome: fa PATCH a /api/profilo/ con il nuovo cognome.
  const submitCognome = async (event) => {
    event.preventDefault()
    setCognomeState({ busy: true, error: '', success: false })
    try {
      const data = await api('/profilo/', { method: 'PATCH', body: JSON.stringify({ cognome: cognomeForm.cognome }) })
      updateUser({ cognome: data.cognome })
      setCognomeState({ busy: false, error: '', success: true })
    } catch (err) {
      setCognomeState({ busy: false, error: err.data?.cognome?.[0] || err.message, success: false })
    }
  }

  // Gestore dell'invio del form per cambiare la password: fa POST a /api/auth/password/ con la password attuale e la nuova password.
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
        busy: false, error: err.data?.password_attuale?.[0] || err.data?.nuova_password?.[0] || err.message, success: false,
      })
    }
  }

  return <div className="page narrow">
    {/* Form per cambiare l'email: richiede la nuova email. */}
    <h1>Profilo</h1>
    <div className="profile-card">
      <div className="avatar" aria-hidden="true">{user.email[0].toUpperCase()}</div>
      <div>
        <small>Email</small>
        <h2>{user.email}</h2>
        <h3>{user.nome} {user.cognome}</h3>
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

    <form className="settings-card" onSubmit={submitName}>
      <h2>Cambia nome e cognome</h2>
      <p>Aggiorna il nome e il cognome visualizzati sul profilo.</p>
      <label>Nome
        <input
          type="text" required value={nameForm.nome}
          onChange={e => { setNameForm({ ...nameForm, nome: e.target.value }); setNameState(s => ({ ...s, error: '', success: false })) }}
          aria-describedby="name-helper" aria-invalid={Boolean(nameState.error)}
        />
      </label>
      <label>Cognome
        <input
          type="text" required value={nameForm.cognome}
          onChange={e => { setNameForm({ ...nameForm, cognome: e.target.value }); setNameState(s => ({ ...s, error: '', success: false })) }}
          aria-describedby="name-helper" aria-invalid={Boolean(nameState.error)}
        />
      </label>
      <div id="name-helper" className="field-helper" aria-live="polite">
        {nameState.error && <span className="field-error" role="alert">{nameState.error}</span>}
        {!nameState.error && nameState.success && <span className="field-success">✓ Nome e cognome aggiornati.</span>}
      </div>
      <button className="primary" disabled={nameState.busy}>{nameState.busy ? 'Attendi…' : 'Salva nome e cognome'}</button>
    </form>

    {/* Form per cambiare la password: richiede la password attuale e la nuova password. */}
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
