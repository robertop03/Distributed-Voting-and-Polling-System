import { fetchStatus } from "./api.js"
import { els } from "./dom.js"

function badgeClass(state) {
  const s = (state || "").toUpperCase()
  if (s === "ALIVE") return "alive"
  if (s === "SUSPECT") return "suspect"
  if (s === "DEAD") return "dead"
  return "unknown"
}

export async function refreshStatus() {
  const data = await fetchStatus()

  const tbody = els.statusTableBody()
  tbody.innerHTML = ""

  const peers = data.peers || []
  if (peers.length === 0) {
    tbody.innerHTML = `<tr><td class="muted" colspan="2">(no peers configured)</td></tr>`
  } else {
    for (const p of peers) {
      const cls = badgeClass(p.state)

      const tr = document.createElement("tr")

      const tdPeer = document.createElement("td")

      const match = String(p.peer).match(/node(\d+)/)
      const nodeNum = match ? match[1] : null

      if (nodeNum) {
        const url = `${window.location.origin}/node/${nodeNum}/ui/`

        const a = document.createElement("a")
        a.href = url
        a.textContent = url
        a.className = "peer-link"
        a.target = "_blank"

        tdPeer.appendChild(a)
      } else {
        tdPeer.textContent = p.peer
      }
      const tdState = document.createElement("td")
      tdState.className = `badge ${cls}`
      tdState.textContent = p.state

      tr.appendChild(tdPeer)
      tr.appendChild(tdState)
      tbody.appendChild(tr)
    }
  }

  els.statusRaw().textContent = JSON.stringify(data, null, 2)
}
