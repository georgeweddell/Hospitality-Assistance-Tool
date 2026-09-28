// Where the API is. A production build is served by the API server itself, so
// it calls its own address (''); `npm run dev` calls the backend on port 8000.
const BASE_URL = import.meta.env.VITE_API_URL ?? (import.meta.env.PROD ? '' : 'http://localhost:8000')

// The login (backend: auth.py) is an httpOnly cookie the server sets: this page
// never sees the token, and the browser sends the cookie with every request
// (credentials: 'include'; needed while the page and the API are on different
// ports on the laptop). A 401 means the login is missing or has ended: the app
// goes back to the login page (the SIGNED_OUT event).
export const SIGNED_OUT = 'docket:signed-out'

function signedOut() {
  try {
    sessionStorage.clear()   // the last account's chosen period and views
  } catch {
    // nothing stored
  }
  window.dispatchEvent(new Event(SIGNED_OUT))
}

// Only the server can remove an httpOnly cookie. Signed out here even if that call fails.
export function signOut() {
  return fetch(`${BASE_URL}/auth/logout`, { method: 'POST', credentials: 'include' })
    .catch(() => {})
    .then(signedOut)
}

// A 401 from anything but a login attempt ends the session.
function checkSignedIn(response, path) {
  if (response.status === 401 && !path.startsWith('/auth/')) signedOut()
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
  const options = { method, headers: {}, credentials: 'include' }
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
  return fetch(`${BASE_URL}${path}`, { method: 'POST', body, credentials: 'include' }).then((response) => {
    checkSignedIn(response, path)
    if (!response.ok) {
      return errorFromResponse(response, `Upload failed (${response.status})`)
    }
    return response.json()
  })
}
