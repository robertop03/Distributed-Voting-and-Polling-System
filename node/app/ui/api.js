export function baseUrl() {
  return window.location.origin
}

export async function fetchJson(url, opts) {
  const resp = await fetch(url, opts)
  if (!resp.ok) {
    const txt = await resp.text()
    throw new Error(`${resp.status} ${resp.statusText}: ${txt}`)
  }
  return resp.json()
}

export async function fetchPolls() {
  return fetchJson(`${baseUrl()}/polls`)
}

export async function fetchPoll(pollId) {
  return fetchJson(`${baseUrl()}/poll/${encodeURIComponent(pollId)}`)
}

export async function fetchStatus() {
  return fetchJson(`${baseUrl()}/status`)
}

export async function sendVoteRequest(pollId, option) {
  return fetchJson(`${baseUrl()}/vote`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ poll_id: pollId, option }),
  })
}
