export const getToken = () => localStorage.getItem('token')

export async function api(path, { method = 'GET', body, form } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let payload
  if (form) payload = form
  else if (body) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body) }
  const res = await fetch(`/api${path}`, { method, headers, body: payload })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    if (res.status === 401 && token) { localStorage.removeItem('token'); window.location.href = '/login' }
    const d = data.detail
    throw new Error(typeof d === 'string' ? d : 'Request failed')
  }
  return data
}
