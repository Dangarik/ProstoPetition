export const STATUS = Object.freeze({
  moderation: 'На модерації',
  rejected: 'Відхилена',
  active: 'Активна',
  hidden: 'Прихована',
  in_review: 'На розгляді',
  answered: 'З відповіддю',
  closed: 'Закрита',
})

export const PUBLIC_STATUSES = ['active', 'in_review', 'answered', 'closed']

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

export const PAGE_SIZE = 20

export function voteLabel(count, threshold) {
  return threshold ? `${count} / ${threshold} голосів` : `${count} голосів`
}
