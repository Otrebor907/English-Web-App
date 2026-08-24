/**
 * Componente riutilizzabile ❌ → ✅ → perché.
 * Accessibile: usa una list semantica per le tre righe e aria-label sulle icone.
 * Riutilizzabile in ogni sezione di lezione ed esercizio guidato.
 */
export default function ErrorBox({ wrong, right, why, className = '' }) {
  return <aside className={`error-box ${className}`} aria-label="Errore tipico degli italiani">
    <ul>
      <li className="error-row">
        <span className="error-icon wrong" aria-hidden="true">✕</span>
        <span className="sr-only">Sbagliato:</span>
        <p>{wrong}</p>
      </li>
      <li className="error-row">
        <span className="error-icon right" aria-hidden="true">✓</span>
        <span className="sr-only">Corretto:</span>
        <p>{right}</p>
      </li>
    </ul>
    <div className="why">
      <b>Perché</b>
      <p>{why}</p>
    </div>
  </aside>
}
