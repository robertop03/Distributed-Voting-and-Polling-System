export function baseUrl() {
  const path = window.location.pathname
  const uiIndex = path.indexOf("/ui/")
  const basePath = uiIndex >= 0 ? path.substring(0, uiIndex) : ""
  return `${window.location.origin}${basePath}`
}

export async function fetchJson(url, opts) {
  const resp = await fetch(url, opts)
  if (!resp.ok) {
    if (resp.status === 502 || resp.status === 503 || resp.status === 504) {
      throw new Error("This node is temporarily unavailable or restarting.")
    }
    throw new Error(`${resp.status} ${resp.statusText}`)
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
