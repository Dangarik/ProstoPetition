const API_ROOT = '/api'

export class ApiError extends Error {
  constructor(message, status = 0, fields = {}, network = false) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fields = fields
    this.network = network
  }
}

let csrfToken = null
let forbiddenHandler = null

export function setForbiddenHandler(handler) {
  forbiddenHandler = handler
}

export function clearCsrfToken() {
  csrfToken = null
}

async function readJson(response) {
  if (response.status === 204) return null
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    if (response.status >= 500) {
      throw new ApiError('Сервер недоступний. Спробуйте ще раз пізніше.', response.status, {}, true)
    }
    throw new ApiError('Сервер повернув некоректну відповідь.', response.status)
  }
}

function errorMessage(data, status) {
  if (typeof data?.detail === 'string') return data.detail
  if (data?.errors || (data && typeof data === 'object')) {
    const values = Object.values(data.errors || data).flat()
    const message = values.find((value) => typeof value === 'string')
    if (message) return message
  }
  return status === 403 ? 'Недостатньо прав або прострочений CSRF-токен.' : 'Не вдалося виконати запит.'
}

export async function request(path, { method = 'GET', body, signal } = {}) {
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (!['GET', 'HEAD'].includes(method.toUpperCase())) {
    if (!csrfToken) await getCsrfToken()
    headers['X-CSRFToken'] = csrfToken
  }

  let response
  try {
    response = await fetch(API_ROOT + path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: 'same-origin',
      signal,
    })
  } catch (error) {
    if (error?.name === 'AbortError') throw error
    throw new ApiError('Немає з’єднання із сервером. Перевірте мережу та спробуйте ще раз.', 0, {}, true)
  }

  const data = await readJson(response)
  if (response.status === 403) {
    clearCsrfToken()
    forbiddenHandler?.(path)
  }
  if (!response.ok) {
    throw new ApiError(errorMessage(data, response.status), response.status, data?.errors || data || {})
  }
  return data
}

export async function getCsrfToken() {
  const data = await request('/auth/csrf/')
  csrfToken = data.csrfToken
  return csrfToken
}

function queryPath(path, params = {}) {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== '' && value !== null && value !== undefined) query.set(key, String(value))
  }
  const encoded = query.toString()
  return path + (encoded ? '?' + encoded : '')
}

export const api = {
  profile: () => request('/auth/profile/'),
  login: (data) => request('/auth/login/', { method: 'POST', body: data }),
  register: (data) => request('/auth/register/', { method: 'POST', body: data }),
  logout: () => request('/auth/logout/', { method: 'POST', body: {} }),
  categories: () => request('/categories/'),
  deleteCategory: (id) => request('/categories/' + encodeURIComponent(id) + '/', { method: 'DELETE' }),
  createCategory: (data) => request('/categories/', { method: 'POST', body: data }),
  updateCategory: (id, data) => request('/categories/' + encodeURIComponent(id) + '/', { method: 'PATCH', body: data }),
  listPetitions: (params = {}, options = {}) => request(queryPath('/petitions/', params), options),
  petition: (id) => request('/petitions/' + encodeURIComponent(id) + '/'),
  createPetition: (data) => request('/petitions/', { method: 'POST', body: data }),
  deletePetition: (id) => request('/petitions/' + encodeURIComponent(id) + '/', { method: 'DELETE' }),
  vote: (id) => request('/petitions/' + encodeURIComponent(id) + '/vote/', { method: 'POST', body: {} }),
  moderationList: (page = 1) => request(queryPath('/admin/petitions/', { page })),
  statistics: () => request('/admin/statistics/'),
  changeStatus: (id, data) => request('/petitions/' + encodeURIComponent(id) + '/status/', { method: 'PATCH', body: data }),
  publishResponse: (id, data) => request('/petitions/' + encodeURIComponent(id) + '/response/', { method: 'POST', body: data }),
}


