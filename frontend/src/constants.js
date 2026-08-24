// Costanti condivise da più pagine/componenti. Vivono in un file a parte così
// esiste UNA sola definizione: se domani cambia l'etichetta di un'area, si
// modifica qui e si aggiorna ovunque (sidebar, card, filtri, pagina lezione).

export const AREA = {
  GRA: { label: 'Grammatica', icon: 'Aa', className: 'grammar' },
  VOC: { label: 'Vocabolario', icon: 'Ab', className: 'vocabulary' },
  COM: { label: 'Comunicazione', icon: 'Hi', className: 'communication' },
}

export const STATUS_LABELS = {
  disponibile: 'Non iniziata',
  in_corso: 'In corso',
  completata: 'Completata',
  in_preparazione: 'In preparazione',
}
