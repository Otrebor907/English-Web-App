import { useEffect, useState } from 'react'

// Hook riutilizzabile per caricare dati dal backend: gestisce loading/data/error
// una volta sola, così ogni pagina non deve riscrivere lo stesso schema.
// `loader` è una funzione che ritorna una Promise (di solito una chiamata ad api()).
export function useLoad(loader, dependencies = []) {
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
