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

export function getJson(path) {
  return fetch(`${BASE_URL}${path}`).then((response) => {
    if (!response.ok) {
      return errorFromResponse(response, `Backend returned ${response.status}`)
    }
    return response.json()
  })
}

export function postJson(path, body) {
  return fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then((response) => {
    if (!response.ok) {
      return errorFromResponse(response, `Request failed (${response.status})`)
    }
    return response.json()
  })
}
