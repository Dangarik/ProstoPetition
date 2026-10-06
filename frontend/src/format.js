export const STATUS = Object.freeze({
  moderation: 'На модерації',
  rejected: 'Відхилена',
  active: 'Активна',
  in_review: 'На розгляді',
  answered: 'З відповіддю',
  closed: 'Закрита',
  expired: 'Термін дії минув',
})

export const PUBLIC_STATUSES = ['active', 'in_review', 'answered', 'closed', 'expired']

export function statusLabel(value) {
  return STATUS[value] || value || 'Невідомий'
}

export function dateLabel(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : new Intl.DateTimeFormat('uk-UA', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

export function excerpt(text, limit = 190) {
  if (!text) return ''
  return text.length > limit ? text.slice(0, limit).trimEnd() + '…' : text
}

export function confirmedVoteKey(userId, petitionId) {
  return 'vote-confirmed:' + userId + ':' + petitionId
}

