import { STATUS_LABELS } from '../constants'

// Pillola colorata che traduce lo stato di una lezione ("in_corso" → "In corso").
export default function StatusPill({ status }) {
  return <span className={`status ${status}`}>{STATUS_LABELS[status] || status}</span>
}
