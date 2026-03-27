const STORAGE_KEY = "pickupQueueState_v1";
const channel = new BroadcastChannel("pickupQueue");

const court1List = document.getElementById("display-court1");
const court2List = document.getElementById("display-court2");
const queueLeft = document.getElementById("display-queue-left");
const queueRight = document.getElementById("display-queue-right");

render();

window.addEventListener("storage", (event) => {
  if (event.key === STORAGE_KEY) {
    render();
  }
});

channel.addEventListener("message", (event) => {
  if (event.data?.type === "state") {
    render();
  }
});

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    return JSON.parse(raw);
  } catch (err) {
    return null;
  }
}

function render() {
  const state = loadState();
  if (!state) {
    return;
  }
  court1List.innerHTML = "";
  court2List.innerHTML = "";
  queueLeft.innerHTML = "";
  queueRight.innerHTML = "";

  state.lastPlayedCourt1.forEach((name) => {
    const li = document.createElement("li");
    li.textContent = name;
    court1List.appendChild(li);
  });
  state.lastPlayedCourt2.forEach((name) => {
    const li = document.createElement("li");
    li.textContent = name;
    court2List.appendChild(li);
  });
  const visibleQueue = state.queue.slice(0, 20);
  const splitIndex = Math.ceil(visibleQueue.length / 2);
  queueLeft.start = 1;
  queueRight.start = splitIndex + 1;
  visibleQueue.forEach((name, index) => {
    const li = document.createElement("li");
    li.textContent = name;
    if (index < splitIndex) {
      queueLeft.appendChild(li);
    } else {
      queueRight.appendChild(li);
    }
  });
}
