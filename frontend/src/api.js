const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// The login token (backend: auth.py), kept in this browser. Every request sends
// it as "Authorization: Bearer <token>". A 401 means it's missing or has ended:
// it's forgotten and the app goes back to the login page (the SIGNED_OUT event).
// Browser storage can be unavailable, so every access is guarded.
const TOKEN_KEY = 'docket-token'
export const SIGNED_OUT = 'docket:signed-out'

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token) {
  try {
    localStorage.setItem(TOKEN_KEY, token)
  } catch {
    // not stored: the login lasts until the page is reloaded
  }
}

export function signOut() {
  try {
    localStorage.removeItem(TOKEN_KEY)
    sessionStorage.clear()   // the last account's chosen period and views
  } catch {
    // nothing stored
  }
  window.dispatchEvent(new Event(SIGNED_OUT))
}

function authHeaders() {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// A 401 from anything but a login attempt ends the session.
function checkSignedIn(response, path) {
  if (response.status === 401 && !path.startsWith('/auth/')) signOut()
}

// Use the backend's own message (FastAPI's "detail") when it sent a plain-text one.
// Otherwise fall back to a generic message with the status code.
function errorFromResponse(response, fallback) {
  return response.json()
    .then((body) => (typeof body.detail === 'string' ? body.detail : fallback))
    .catch(() => fallback)
    .then((message) => {
      throw new Error(message)
    })
}

function request(method, path, body) {
  const options = { method, headers: authHeaders() }
  if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(body)
  }
  return fetch(`${BASE_URL}${path}`, options).then((response) => {
    checkSignedIn(response, path)
    if (!response.ok) {
      return errorFromResponse(response, `Request failed (${response.status})`)
    }
    return response.status === 204 ? null : response.json()
  })
}

export const getJson = (path) => request('GET', path)
export const postJson = (path, body) => request('POST', path, body)
export const putJson = (path, body) => request('PUT', path, body)
export const deleteJson = (path) => request('DELETE', path)

// Uploads one file as a form (the backend reads it as `file`).
export function postFile(path, file) {
  const body = new FormData()
  body.append('file', file)
  return fetch(`${BASE_URL}${path}`, { method: 'POST', body, headers: authHeaders() }).then((response) => {
    checkSignedIn(response, path)
    if (!response.ok) {
      return errorFromResponse(response, `Upload failed (${response.status})`)
    }
    return response.json()
  })
}
