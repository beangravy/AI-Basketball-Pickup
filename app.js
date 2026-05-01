const STORAGE_KEY = "pickupQueueState_v1";
const channel = new BroadcastChannel("pickupQueue");

const state = loadState();

const queueList = document.getElementById("queue-list");
const court1List = document.getElementById("court1-list");
const court2List = document.getElementById("court2-list");
const playerInput = document.getElementById("player-input");

const statQueue = document.getElementById("stat-queue");
const statCourts = document.getElementById("stat-courts");
const statLastPlay = document.getElementById("stat-last-play");

document.getElementById("add-btn").addEventListener("click", addPlayers);
document.getElementById("clear-btn").addEventListener("click", clearQueue);
document.getElementById("select-next-btn").addEventListener("click", selectNext);
document.getElementById("play-btn").addEventListener("click", playSelected);
document.getElementById("undo-btn").addEventListener("click", undoPlay);
document.getElementById("swap-btn").addEventListener("click", swapSelected);
document
  .getElementById("clear-selection-btn")
  .addEventListener("click", clearSelection);
document.getElementById("remove-btn").addEventListener("click", removeSelected);
document.getElementById("rename-btn").addEventListener("click", renameSelected);
document.getElementById("lock-btn").addEventListener("click", lockControls);
document.getElementById("unlock-btn").addEventListener("click", unlockControls);
document.getElementById("display-btn").addEventListener("click", () => {
  window.open("display.html", "_blank", "noopener");
});
document.getElementById("export-btn").addEventListener("click", exportState);
document.getElementById("import-input").addEventListener("change", importState);

document.querySelectorAll('input[name="courts"]').forEach((radio) => {
  radio.addEventListener("change", (event) => {
    state.courts = Number(event.target.value);
    persist();
    render();
  });
});

document.querySelectorAll('input[name="add-mode"]').forEach((radio) => {
  radio.addEventListener("change", (event) => {
    state.addMode = event.target.value;
    persist();
  });
});

playerInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    addPlayers();
  }
});

render();

function defaultState() {
  return {
    queue: [],
    games: {},
    courts: 1,
    addMode: "first_in",
    selectedIndices: [],
    lastPlayedCourt1: [],
    lastPlayedCourt2: [],
    undoSnapshot: null,
    addedSincePlay: [],
    pendingAfterPlay: [],
    locked: false,
    lockCode: "6600",
    courtSelections: { court1: null, court2: null },
  };
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return defaultState();
    }
    const parsed = JSON.parse(raw);
    return { ...defaultState(), ...parsed };
  } catch (err) {
    return defaultState();
  }
}

function persist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  channel.postMessage({ type: "state", payload: state });
}

function render() {
  renderQueue();
  renderCourts();
  updateStats();
  syncControls();
}

function renderQueue() {
  queueList.innerHTML = "";
  state.queue.forEach((name, index) => {
    const li = document.createElement("li");
    li.draggable = true;
    li.dataset.index = index;
    if (state.selectedIndices.includes(index)) {
      li.classList.add("selected");
    }
    const games = state.games[name] || 0;
    li.innerHTML = `<span>${index + 1}. ${escapeHtml(name)}</span>
      <span class="badge">${games} games</span>`;
    li.addEventListener("click", (event) => {
      event.preventDefault();
      toggleSelection(index);
    });
    li.addEventListener("dragstart", (event) => {
      if (state.locked) {
        event.preventDefault();
        return;
      }
      event.dataTransfer.setData("text/plain", String(index));
    });
    li.addEventListener("dragover", (event) => {
      event.preventDefault();
    });
    li.addEventListener("drop", (event) => {
      event.preventDefault();
      if (state.locked) {
        alert("Unlock to reorder the queue.");
        return;
      }
      const fromIndex = Number(event.dataTransfer.getData("text/plain"));
      const toIndex = Number(li.dataset.index);
      if (Number.isNaN(fromIndex) || Number.isNaN(toIndex)) {
        return;
      }
      if (fromIndex === toIndex) {
        return;
      }
      if (!confirm("Move the selected player to the new position?")) {
        return;
      }
      const [item] = state.queue.splice(fromIndex, 1);
      state.queue.splice(toIndex, 0, item);
      state.selectedIndices = [toIndex];
      persist();
      render();
    });
    queueList.appendChild(li);
  });
}

function renderCourts() {
  court1List.innerHTML = "";
  court2List.innerHTML = "";
  state.lastPlayedCourt1.forEach((name, index) => {
    const li = document.createElement("li");
    li.dataset.index = index;
    if (state.courtSelections.court1 === index) {
      li.classList.add("selected");
    }
    li.innerHTML = `<span>${index + 1}. ${escapeHtml(name)}</span>`;
    li.addEventListener("click", () => {
      state.courtSelections.court1 =
        state.courtSelections.court1 === index ? null : index;
      persist();
      render();
    });
    court1List.appendChild(li);
  });
  state.lastPlayedCourt2.forEach((name, index) => {
    const li = document.createElement("li");
    li.dataset.index = index;
    if (state.courtSelections.court2 === index) {
      li.classList.add("selected");
    }
    li.innerHTML = `<span>${index + 1}. ${escapeHtml(name)}</span>`;
    li.addEventListener("click", () => {
      state.courtSelections.court2 =
        state.courtSelections.court2 === index ? null : index;
      persist();
      render();
    });
    court2List.appendChild(li);
  });
}

function updateStats() {
  statQueue.textContent = String(state.queue.length);
  statCourts.textContent = String(state.courts);
  const lastPlayCount = state.lastPlayedCourt1.length + state.lastPlayedCourt2.length;
  statLastPlay.textContent = String(lastPlayCount);
  document.querySelectorAll('input[name="courts"]').forEach((radio) => {
    radio.checked = Number(radio.value) === state.courts;
  });
  document.querySelectorAll('input[name="add-mode"]').forEach((radio) => {
    radio.checked = radio.value === state.addMode;
  });
}

function syncControls() {
  document.querySelectorAll("[data-lockable='true']").forEach((btn) => {
    btn.disabled = state.locked;
  });
}

function toggleSelection(index) {
  if (state.selectedIndices.includes(index)) {
    state.selectedIndices = state.selectedIndices.filter((i) => i !== index);
  } else {
    state.selectedIndices.push(index);
  }
  persist();
  renderQueue();
}

function addPlayers() {
  if (state.locked) {
    alert("Unlock to add players.");
    return;
  }
  const raw = playerInput.value.trim();
  if (!raw) {
    return;
  }
  const names = raw
    .split(",")
    .map((name) => name.trim())
    .filter(Boolean);
  if (!names.length) {
    return;
  }
  const existing = new Set(Object.keys(state.games));
  const dupes = names.filter((name) => existing.has(name));
  let filtered = names;
  if (dupes.length) {
    alert(`These names already exist and were not added:\n${dupes.join(", ")}`);
    filtered = names.filter((name) => !existing.has(name));
    if (!filtered.length) {
      return;
    }
  }
  filtered.forEach((name) => {
    if (!state.games[name]) {
      state.games[name] = 0;
    }
  });
  state.addedSincePlay.push(...filtered);
  const insertAt = getInsertIndex();
  state.queue.splice(insertAt, 0, ...filtered);
  playerInput.value = "";
  state.selectedIndices = [];
  persist();
  render();
}

function clearQueue() {
  if (state.locked) {
    alert("Unlock to clear the queue.");
    return;
  }
  if (confirm("Clear the entire queue?")) {
    resetQueueSession();
    persist();
    render();
  }
}

function resetQueueSession() {
  state.queue = [];
  state.games = {};
  state.selectedIndices = [];
  state.lastPlayedCourt1 = [];
  state.lastPlayedCourt2 = [];
  state.undoSnapshot = null;
  state.addedSincePlay = [];
  state.pendingAfterPlay = [];
  state.courtSelections = { court1: null, court2: null };
}

function clearSelection() {
  if (state.locked) {
    alert("Unlock to clear the selection.");
    return;
  }
  state.selectedIndices = [];
  persist();
  renderQueue();
}

function removeSelected() {
  if (state.locked) {
    alert("Unlock to remove players.");
    return;
  }
  if (!state.selectedIndices.length) {
    return;
  }
  const names = state.selectedIndices
    .map((index) => state.queue[index])
    .filter(Boolean);
  const label = names.length === 1 ? names[0] : `${names.length} players`;
  if (!confirm(`Remove ${label} from the queue?`)) {
    return;
  }
  const sorted = [...state.selectedIndices].sort((a, b) => b - a);
  sorted.forEach((index) => {
    state.queue.splice(index, 1);
  });
  state.selectedIndices = [];
  persist();
  render();
}

function renameSelected() {
  if (state.selectedIndices.length !== 1) {
    alert("Select one player to rename.");
    return;
  }
  const idx = state.selectedIndices[0];
  const oldName = state.queue[idx];
  const newName = prompt(`Edit name for: ${oldName}`, oldName);
  if (newName === null) {
    return;
  }
  const trimmed = newName.trim();
  if (!trimmed) {
    return;
  }
  if (trimmed !== oldName && state.games[trimmed]) {
    alert("That name already exists.");
    return;
  }
  state.queue[idx] = trimmed;
  if (state.games[oldName] !== undefined) {
    state.games[trimmed] = state.games[oldName];
    delete state.games[oldName];
  }
  state.lastPlayedCourt1 = state.lastPlayedCourt1.map((name) =>
    name === oldName ? trimmed : name
  );
  state.lastPlayedCourt2 = state.lastPlayedCourt2.map((name) =>
    name === oldName ? trimmed : name
  );
  state.addedSincePlay = state.addedSincePlay.map((name) =>
    name === oldName ? trimmed : name
  );
  state.pendingAfterPlay = state.pendingAfterPlay.map((name) =>
    name === oldName ? trimmed : name
  );
  state.selectedIndices = [idx];
  persist();
  render();
}

function selectNext() {
  if (!state.queue.length) {
    alert("Queue is empty.");
    return;
  }
  const count = Math.min(state.queue.length, 10 * state.courts);
  state.selectedIndices = Array.from({ length: count }, (_, i) => i);
  persist();
  renderQueue();
}

function playSelected() {
  if (!state.selectedIndices.length) {
    alert("No players selected. Use Select Next 10/20 first.");
    return;
  }
  state.undoSnapshot = {
    queue: [...state.queue],
    games: { ...state.games },
    court1: [...state.lastPlayedCourt1],
    court2: [...state.lastPlayedCourt2],
  };
  state.addedSincePlay = [];
  const selected = state.selectedIndices.map((index) => state.queue[index]);
  selected.forEach((name) => {
    state.games[name] = (state.games[name] || 0) + 1;
  });
  const sorted = [...state.selectedIndices].sort((a, b) => b - a);
  sorted.forEach((index) => state.queue.splice(index, 1));
  state.queue.push(...selected);
  if (state.pendingAfterPlay.length) {
    const insertAt = getInsertIndex();
    state.queue.splice(insertAt, 0, ...state.pendingAfterPlay);
    state.pendingAfterPlay = [];
  }
  if (state.courts === 2) {
    state.lastPlayedCourt1 = selected.slice(0, 10);
    state.lastPlayedCourt2 = selected.slice(10, 20);
  } else {
    state.lastPlayedCourt1 = [...selected];
    state.lastPlayedCourt2 = [];
  }
  state.selectedIndices = [];
  persist();
  render();
}

function undoPlay() {
  if (!state.undoSnapshot) {
    return;
  }
  if (state.addedSincePlay.length) {
    const addNow = confirm("Add players who joined after the last Play now?");
    if (addNow) {
      const insertAt = getInsertIndex();
      state.queue = [...state.undoSnapshot.queue];
      state.queue.splice(insertAt, 0, ...state.addedSincePlay);
    } else if (confirm("Add those players after the next Play instead?")) {
      state.pendingAfterPlay = [...state.addedSincePlay];
      state.queue = [...state.undoSnapshot.queue];
    } else {
      state.queue = [...state.undoSnapshot.queue];
    }
  } else {
    state.queue = [...state.undoSnapshot.queue];
  }
  state.games = { ...state.undoSnapshot.games };
  state.lastPlayedCourt1 = [...state.undoSnapshot.court1];
  state.lastPlayedCourt2 = [...state.undoSnapshot.court2];
  state.undoSnapshot = null;
  state.addedSincePlay = [];
  state.selectedIndices = [];
  persist();
  render();
}

function swapSelected() {
  const idx1 = state.courtSelections.court1;
  const idx2 = state.courtSelections.court2;
  if (idx1 === null || idx2 === null) {
    alert("Select one player in each court list to swap.");
    return;
  }
  if (
    idx1 >= state.lastPlayedCourt1.length ||
    idx2 >= state.lastPlayedCourt2.length
  ) {
    return;
  }
  const temp = state.lastPlayedCourt1[idx1];
  state.lastPlayedCourt1[idx1] = state.lastPlayedCourt2[idx2];
  state.lastPlayedCourt2[idx2] = temp;
  persist();
  renderCourts();
}

function lockControls() {
  state.locked = true;
  persist();
  syncControls();
}

function unlockControls() {
  const code = prompt("Enter unlock code:");
  if (code === null) {
    return;
  }
  if (code === state.lockCode) {
    state.locked = false;
    persist();
    syncControls();
  } else {
    alert("Incorrect code.");
  }
}

function getInsertIndex() {
  if (state.addMode === "first_in") {
    let lastZero = -1;
    state.queue.forEach((name, index) => {
      if ((state.games[name] || 0) === 0) {
        lastZero = index;
      }
    });
    return lastZero + 1;
  }
  if (state.addMode === "after_sitting") {
    const onCourtCount =
      state.lastPlayedCourt1.length + state.lastPlayedCourt2.length;
    if (!onCourtCount) {
      return state.queue.length;
    }
    return Math.max(0, state.queue.length - onCourtCount);
  }
  return state.queue.length;
}

function exportState() {
  const blob = new Blob([JSON.stringify(state, null, 2)], {
    type: "application/json",
  });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "pickup-queue-state.json";
  link.click();
  URL.revokeObjectURL(link.href);
}

function importState(event) {
  const file = event.target.files[0];
  if (!file) {
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const parsed = JSON.parse(reader.result);
      Object.assign(state, defaultState(), parsed);
      persist();
      render();
    } catch (err) {
      alert("Invalid JSON file.");
    } finally {
      event.target.value = "";
    }
  };
  reader.readAsText(file);
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
