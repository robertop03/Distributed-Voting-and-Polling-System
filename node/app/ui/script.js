function baseUrl() {
  return window.location.origin
}

function setError(msg) {
  document.getElementById("error").textContent = msg || ""
}

function badgeClass(state) {
  const s = (state || "").toUpperCase()
  if (s === "ALIVE") return "alive"
  if (s === "SUSPECT") return "suspect"
  if (s === "DEAD") return "dead"
  return "unknown"
}

async function fetchJson(url, opts) {
  const resp = await fetch(url, opts)
  if (!resp.ok) {
    const txt = await resp.text()
    throw new Error(`${resp.status} ${resp.statusText}: ${txt}`)
  }
  return resp.json()
}

async function refreshPoll() {
  const pollId = document.getElementById("pollId").value.trim()
  const data = await fetchJson(`${baseUrl()}/poll/${encodeURIComponent(pollId)}`)

  const tbody = document.querySelector("#pollTable tbody")
  tbody.innerHTML = ""

  const counts = data.counts || {}
  const keys = Object.keys(counts).sort()

  if (keys.length === 0) {
    tbody.innerHTML = `<tr><td class="muted" colspan="2">(no votes yet)</td></tr>`
  } else {
    for (const opt of keys) {
      const tr = document.createElement("tr")
      tr.innerHTML = `<td>${opt}</td><td>${counts[opt]}</td>`
      tbody.appendChild(tr)
    }
  }

  document.getElementById("pollRaw").textContent = JSON.stringify(data, null, 2)
}

async function refreshStatus() {
  const data = await fetchJson(`${baseUrl()}/status`)

  const tbody = document.querySelector("#statusTable tbody")
  tbody.innerHTML = ""

  const peers = data.peers || []
  if (peers.length === 0) {
    tbody.innerHTML = `<tr><td class="muted" colspan="2">(no peers configured)</td></tr>`
  } else {
    for (const p of peers) {
      const cls = badgeClass(p.state)
      const tr = document.createElement("tr")
      tr.innerHTML = `<td>${p.peer}</td><td class="badge ${cls}">${p.state}</td>`
      tbody.appendChild(tr)
    }
  }

  document.getElementById("statusRaw").textContent = JSON.stringify(data, null, 2)
}

async function refreshAll() {
  setError("")
  try {
    await Promise.all([refreshPoll(), refreshStatus()])
    document.getElementById("lastUpdate").textContent = `Last update: ${new Date().toLocaleTimeString()}`
  } catch (e) {
    setError(String(e.message || e))
  }
}

async function sendVote() {
  setError("")
  const pollId = document.getElementById("pollId").value.trim()
  const option = document.getElementById("option").value.trim()
  const url = `${baseUrl()}/vote`

  const btn = document.getElementById("voteBtn")
  btn.disabled = true

  try {
    await fetchJson(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ poll_id: pollId, option: option }),
    })
    await refreshAll()
  } catch (e) {
    setError(String(e.message || e))
  } finally {
    btn.disabled = false
  }
}

document.getElementById("voteBtn").addEventListener("click", sendVote)
document.getElementById("currentOrigin").textContent = window.location.origin

refreshAll()
setInterval(refreshAll, 2000)
