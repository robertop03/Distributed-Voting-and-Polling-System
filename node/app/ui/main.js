import { sendVoteRequest } from "./api.js"
import { els, setError } from "./dom.js"
import { uiState } from "./state.js"
import { refreshPoll, refreshPollList, renderSelectedPollInList } from "./polls.js"
import { refreshStatus } from "./status.js"

async function refreshAll() {
  setError("")

  try {
    const isEditingPollId = document.activeElement === els.pollId()

    await refreshPollList()
    await refreshStatus()

    if (!isEditingPollId) {
      await refreshPoll()
    }

    els.lastUpdate().textContent = `Last update: ${new Date().toLocaleTimeString()}`
  } catch (e) {
    setError(String(e.message || e))
  }
}

async function sendVote() {
  setError("")

  const pollId = els.pollId().value.trim()
  const option = els.option().value.trim()

  if (!pollId) {
    setError("Select a poll first")
    return
  }

  const btn = els.voteBtn()
  btn.disabled = true

  try {
    await sendVoteRequest(pollId, option)
    await refreshAll()
  } catch (e) {
    setError(String(e.message || e))
  } finally {
    btn.disabled = false
  }
}

function bindEvents() {
  els.voteBtn().addEventListener("click", sendVote)

  els.pollId().addEventListener("blur", refreshPoll)

  els.pollId().addEventListener("input", (e) => {
    renderSelectedPollInList(e.target.value.trim())
  })
}

function init() {
  els.currentOrigin().textContent = window.location.origin
  bindEvents()
  refreshAll()
  setInterval(refreshAll, uiState.refreshIntervalMs)
}

init()
