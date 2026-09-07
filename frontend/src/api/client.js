const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export const TOKEN_STORAGE_KEY = 'salary_management_auth_token'
let unauthorizedHandler = () => {}

export class ApiError extends Error {
  constructor(message, status, body = null) {
    super(message)
    this.status = status
    this.body = body
  }
}

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler
}

export function getStoredToken() {
  return window.localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function storeToken(token) {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token)
}

export function clearStoredToken() {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY)
}

export async function apiFetch(path, options = {}) {
  const token = getStoredToken()
  const headers = new Headers(options.headers)
  if (!(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
  const body = response.status === 204 ? null : await response.json()
  if (response.status === 401) unauthorizedHandler()
  if (!response.ok) throw new ApiError(body?.detail ?? 'Request failed', response.status, body)
  return body
}

export const api = {
  login: (credentials) =>
    apiFetch('/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
  register: (registration) =>
    apiFetch('/auth/register', { method: 'POST', body: JSON.stringify(registration) }),
  getCurrentUser: () => apiFetch('/auth/me'),
  getEmployees: (params) => apiFetch(`/employees?${new URLSearchParams(params)}`),
  getEmployee: (employeeId) => apiFetch(`/employees/${employeeId}`),
  updateEmployee: (employeeId, payload) =>
    apiFetch(`/employees/${employeeId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  addSalary: (employeeId, payload) =>
    apiFetch(`/employees/${employeeId}/salaries`, { method: 'POST', body: JSON.stringify(payload) }),
  importEmployees: (file) => {
    const body = new FormData()
    body.append('file', file)
    return apiFetch('/employees/import', { method: 'POST', body })
  },
  getHeadcount: () => apiFetch('/analytics/headcount'),
  getSalarySummary: () => apiFetch('/analytics/salary-summary'),
  getBandDistribution: (params = {}) => {
    const query = new URLSearchParams(
      Object.entries(params).filter(([, value]) => value),
    )
    return apiFetch(`/analytics/band-distribution?${query}`)
  },
  getSalaryRange: () => apiFetch('/analytics/salary-range'),
}
