export const els = {
  pollId: () => document.getElementById("pollId"),
  option: () => document.getElementById("option"),
  voteBtn: () => document.getElementById("voteBtn"),
  error: () => document.getElementById("error"),
  currentOrigin: () => document.getElementById("currentOrigin"),
  lastUpdate: () => document.getElementById("lastUpdate"),
  pollList: () => document.getElementById("pollList"),
  pollTableBody: () => document.querySelector("#pollTable tbody"),
  pollRaw: () => document.getElementById("pollRaw"),
  statusTableBody: () => document.querySelector("#statusTable tbody"),
  statusRaw: () => document.getElementById("statusRaw"),
}

export function setError(msg) {
  els.error().textContent = msg || ""
}
