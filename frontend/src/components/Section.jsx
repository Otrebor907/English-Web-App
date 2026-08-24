import ErrorBox from './ErrorBox'

// Una singola sezione di contenuto della lezione. Il campo formato_web decide
// come renderizzarla: box errore, lista, oppure testo+esempio (default).
function Section({ section }) {
  const content = section.contenuto || {}
  if (section.formato_web === 'errore_box') {
    // Supporta sia il box singolo storico sia una lista di errori (content.errori).
    const errori = Array.isArray(content.errori) && content.errori.length
      ? content.errori
      : [{ errato: content.errato, corretto: content.corretto, perche: content.perche }]
    return <div className="content-section">
      {content.titolo && <><span className="section-label">{section.tipo_sezione}</span><h2>{content.titolo}</h2></>}
      {errori.map((e, i) => <ErrorBox key={i} wrong={e.errato} right={e.corretto} why={e.perche} />)}
    </div>
  }
  if (section.formato_web === 'lista') {
    return <div className="content-section">
      <span className="section-label">{section.tipo_sezione}</span>
      <h2>{content.titolo || section.tipo_sezione}</h2>
      <ul>{(content.elementi || []).map((item, i) => <li key={i}>{item}</li>)}</ul>
    </div>
  }
  const body = content.testo
  return <div className="content-section">
    <span className="section-label">{section.tipo_sezione}</span>
    <h2>{content.titolo || section.tipo_sezione}</h2>
    {body && <p>{body}</p>}
    {content.esempio && <blockquote>
      <strong>{content.esempio}</strong>
      {content.traduzione && <small>{content.traduzione}</small>}
    </blockquote>}
  </div>
}

// Elenco ordinato delle sezioni di una lezione.
export default function SectionList({ sezioni }) {
  return <div className="section-list" aria-label="Contenuto della lezione">
    {sezioni.map((section, i) => <Section key={i} section={section} />)}
  </div>
}
