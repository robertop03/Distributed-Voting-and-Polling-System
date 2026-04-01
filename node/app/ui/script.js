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

function setSelectedPoll(pollId) {
  document.getElementById("pollId").value = pollId
  renderSelectedPollInList(pollId)
}

function renderSelectedPollInList(selectedPollId) {
  const items = document.querySelectorAll(".poll-list-item")
  for (const item of items) {
    if (item.dataset.pollId === selectedPollId) {
      item.classList.add("active")
    } else {
      item.classList.remove("active")
    }
  }
}

async function refreshPollList() {
  const data = await fetchJson(`${baseUrl()}/polls`)
  const pollIds = data.poll_ids || []

  const pollList = document.getElementById("pollList")
  const pollInput = document.getElementById("pollId")
  const currentPollId = pollInput.value.trim()

  pollList.innerHTML = ""

  if (pollIds.length === 0) {
    pollList.innerHTML = `<div class="muted">(no polls with votes yet)</div>`
    renderSelectedPollInList(currentPollId)
    return
  }

  // Imposta il default SOLO se il campo è veramente vuoto
  if (!currentPollId) {
    pollInput.value = pollIds[0]
  }

  const selectedPollId = pollInput.value.trim()
  const isExistingPoll = pollIds.includes(selectedPollId)

  for (const pollId of pollIds) {
    const btn = document.createElement("button")
    btn.type = "button"
    btn.className = "poll-list-item"
    btn.dataset.pollId = pollId
    btn.textContent = pollId

    if (isExistingPoll && pollId === selectedPollId) {
      btn.classList.add("active")
    }

    btn.addEventListener("click", async () => {
      setSelectedPoll(pollId)
      await refreshPoll()
    })

    pollList.appendChild(btn)
  }

  renderSelectedPollInList(selectedPollId)
}

async function refreshPoll() {
  const pollId = document.getElementById("pollId").value.trim()
  const tbody = document.querySelector("#pollTable tbody")

  if (!pollId) {
    tbody.innerHTML = `<tr><td class="muted" colspan="2">(select a poll)</td></tr>`
    document.getElementById("pollRaw").textContent = ""
    renderSelectedPollInList("")
    return
  }

  renderSelectedPollInList(pollId)

  const data = await fetchJson(`${baseUrl()}/poll/${encodeURIComponent(pollId)}`)

  tbody.innerHTML = ""

  const counts = data.counts || {}
  const keys = Object.keys(counts).sort()

  if (keys.length === 0) {
    tbody.innerHTML = `<tr><td class="muted" colspan="2">(no votes yet)</td></tr>`
  } else {
    for (const opt of keys) {
      const tr = document.createElement("tr")
      const tdOption = document.createElement("td")
      tdOption.textContent = opt
      const tdCount = document.createElement("td")
      tdCount.textContent = String(counts[opt])
      tr.appendChild(tdOption)
      tr.appendChild(tdCount)
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
      const tdPeer = document.createElement("td")
      tdPeer.textContent = p.peer
      const tdState = document.createElement("td")
      tdState.className = `badge ${cls}`
      tdState.textContent = p.state
      tr.appendChild(tdPeer)
      tr.appendChild(tdState)
      tbody.appendChild(tr)
    }
  }

  document.getElementById("statusRaw").textContent = JSON.stringify(data, null, 2)
}

async function refreshAll() {
  setError("")

  try {
    const pollInput = document.getElementById("pollId")
    const isEditingPollId = document.activeElement === pollInput

    await refreshPollList()
    await refreshStatus()

    if (!isEditingPollId) {
      await refreshPoll()
    }

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

  if (!pollId) {
    setError("Select a poll first")
    return
  }

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

// Quando finisci di scrivere e lasci il campo, aggiorna subito i risultati
document.getElementById("pollId").addEventListener("blur", refreshPoll)

// Quando scrivi, aggiorna solo l'evidenziazione della lista
document.getElementById("pollId").addEventListener("input", (e) => {
  const value = e.target.value.trim()
  const items = document.querySelectorAll(".poll-list-item")

  for (const item of items) {
    if (item.dataset.pollId === value) {
      item.classList.add("active")
    } else {
      item.classList.remove("active")
    }
  }
})

refreshAll()
setInterval(refreshAll, 2000)
