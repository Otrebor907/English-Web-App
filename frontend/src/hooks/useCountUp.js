import { useEffect, useState } from 'react'

// Anima un numero da 0 fino a `target` (usato per il punteggio del quiz).
// Rispetta prefers-reduced-motion: chi ha disattivato le animazioni vede subito
// il valore finale, senza conteggio animato.
export function useCountUp(target, duration = 1200) {
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
