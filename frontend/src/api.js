const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

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
  const options = { method }
  if (body !== undefined) {
    options.headers = { 'Content-Type': 'application/json' }
    options.body = JSON.stringify(body)
  }
  return fetch(`${BASE_URL}${path}`, options).then((response) => {
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
  return fetch(`${BASE_URL}${path}`, { method: 'POST', body }).then((response) => {
    if (!response.ok) {
      return errorFromResponse(response, `Upload failed (${response.status})`)
    }
    return response.json()
  })
}
