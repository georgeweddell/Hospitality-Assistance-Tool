const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function getJson(path) {
  return fetch(`${BASE_URL}${path}`).then((response) => {
    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`)
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
      throw new Error(`Save failed (${response.status})`)
    }
    return response.json()
  })
}