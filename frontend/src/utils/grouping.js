import { AREA } from '../constants'

/** Raggruppa una lista di lezioni (già ordinate per ordine_percorso) per categoria,
 *  preservando l'ordine di prima comparsa. Ritorna [{ categoria, items }]. */
export function groupByCategoria(lessons) {
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
export function groupByAreaAndCategoria(lessons) {
  return Object.entries(AREA)
    .map(([code, info]) => ({ code, info, items: lessons.filter(l => l.area === code) }))
    .filter(group => group.items.length > 0)
    .map(group => ({ ...group, categorie: groupByCategoria(group.items) }))
}
