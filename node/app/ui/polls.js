import { fetchPolls, fetchPoll } from "./api.js"
import { els } from "./dom.js"

export function setSelectedPoll(pollId) {
  els.pollId().value = pollId
  renderSelectedPollInList(pollId)
}

export function renderSelectedPollInList(selectedPollId) {
  const items = document.querySelectorAll(".poll-list-item")

  for (const item of items) {
    if (item.dataset.pollId === selectedPollId) {
      item.classList.add("active")
    } else {
      item.classList.remove("active")
    }
  }
}

export async function refreshPollList() {
  const data = await fetchPolls()
  const pollIds = data.poll_ids || []

  const pollList = els.pollList()
  const pollInput = els.pollId()
  const currentPollId = pollInput.value.trim()

  pollList.innerHTML = ""

  if (pollIds.length === 0) {
    pollList.innerHTML = `<div class="muted">(no polls with votes yet)</div>`
    renderSelectedPollInList("")
    return
  }

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

  renderSelectedPollInList(isExistingPoll ? selectedPollId : "")
}

export async function refreshPoll() {
  const pollId = els.pollId().value.trim()
  const tbody = els.pollTableBody()

  if (!pollId) {
    tbody.innerHTML = `<tr><td class="muted" colspan="2">(select a poll)</td></tr>`
    els.pollRaw().textContent = ""
    renderSelectedPollInList("")
    return
  }

  renderSelectedPollInList(pollId)

  const data = await fetchPoll(pollId)

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

  els.pollRaw().textContent = JSON.stringify(data, null, 2)
}
