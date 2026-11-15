"use strict";

const $ = (id) => document.getElementById(id);

let me = null;
let socket = null;
let reconnectTimer = null;
let state = null;
let myPlayer = null;
let prevCells = null;
let authMode = "login";

async function api(path, options = {}) {
  const res = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  let data = null;
  if (res.status !== 204) {
    try { data = await res.json(); } catch {}
  }

  if (!res.ok) {
    let message = "Что-то пошло не так. Попробуйте ещё раз.";

    if (data && typeof data.detail === "string") {
      message = data.detail;
    } else if (res.status === 422) {
      message = "Имя пользователя должно содержать от 3 до 32 символа (латинские буквы, цифры, _), пароль - от 8 символов.";
    }

    const err = new Error(message);
    err.status = res.status;
    throw err;
  }

  return data;
}

function showAuth() {
  $("game").hidden = true;
  $("auth").hidden = false;
  $("password").value = "";
  $("auth-error").textContent = "";
}

function showGame() {
  $("auth").hidden = true;
  $("game").hidden = false;
  $("whoami").textContent = me.username;
}

function setAuthMode(mode) {
  authMode = mode;
  const isLogin = mode === "login";

  $("tab-login").setAttribute("aria-selected", String(isLogin));
  $("tab-register").setAttribute("aria-selected", String(!isLogin));
  $("auth-submit").textContent = isLogin ? "Войти" : "Создать аккаунт";
  $("password").autocomplete = isLogin ? "current-password" : "new-password";
  $("auth-hint").hidden = isLogin;
  $("auth-error").textContent = "";
}

$("tab-login").addEventListener("click", () => setAuthMode("login"));
$("tab-register").addEventListener("click", () => setAuthMode("register"));

$("auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  const button = $("auth-submit");
  button.disabled = true;
  $("auth-error").textContent = "";

  try {
    me = await api(`/api/auth/${authMode}`, {
      method: "POST",
      body: JSON.stringify({
        username: $("username").value.trim(),
        password: $("password").value,
      }),
    });
    showGame();
    connect();
  } catch (err) {
    $("auth-error").textContent = err.message;
  } finally {
    button.disabled = false;
  }
});

$("logout").addEventListener("click", async () => {
  me = null;
  clearTimeout(reconnectTimer);
  const old = socket;
  socket = null;
  if (old) old.close();
  state = null;
  myPlayer = null;
  prevCells = null;
  try { await api("/api/auth/logout", { method: "POST" }); } catch {}
  showAuth();
});

function connect() {
  clearTimeout(reconnectTimer);
  if (socket) {
    const old = socket;
    socket = null;
    old.close();
  }

  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${proto}//${location.host}/ws`);
  socket = ws;

  ws.onmessage = (event) => {
    if (ws !== socket) return;
    const msg = JSON.parse(event.data);
    if (msg.type === "init" || msg.type === "state") {
      state = msg.state;
      myPlayer = msg.player;
      $("game-error").textContent = "";
      render();
    }
  };

  ws.onclose = async () => {
    if (ws !== socket || me === null) return;

    try {
      await api("/api/auth/me");
      reconnectTimer = setTimeout(connect, 1500);
    } catch (err) {
      if (err.status === 401) {
        me = null;
        socket = null;
        showAuth();
        $("auth-error").textContent = "Сессия закончилась. Войдите снова.";
      } else {
        reconnectTimer = setTimeout(connect, 3000);
      }
    }
  };
}

function statusText() {
  const { status, current_player, winner } = state.game;

  if (myPlayer === null) {
    return status === "finished"
      ? "Игра окончена. Вы в очереди и можете наблюдать."
      : "Все места заняты. Вы в очереди и можете наблюдать.";
  }

  if (status === "finished") {
    if (winner === 0) return "Ничья.";
    return winner === myPlayer ? "Вы победили!" : "Вы проиграли.";
  }

  return current_player === myPlayer ? "Ваш ход." : "Ход соперника.";
}

function canMove() {
  return (
    state !== null &&
    myPlayer !== null &&
    state.game.status === "in_progress" &&
    state.game.current_player === myPlayer
  );
}

function render() {
  if (!state) return;
  const { width, height, cells } = state.board;
  const movable = canMove();
  const board = $("board");

  board.replaceChildren();

  for (let x = 0; x < width; x++) {
    const col = document.createElement("button");
    col.type = "button";
    col.className = "col" + (movable ? " can" : "");
    col.setAttribute("aria-label", `Колонка ${x + 1}`);
    col.disabled = !movable;
    col.addEventListener("click", () => dropPiece(x));

    for (let y = height - 1; y >= 0; y--) {
      const value = cells[x][y];
      const cell = document.createElement("div");
      cell.className = "cell" + (value ? ` p${value}` : "");

      const wasEmpty = prevCells && prevCells[x] && prevCells[x][y] === 0;
      if (value && wasEmpty) cell.classList.add("drop");

      col.appendChild(cell);
    }
    board.appendChild(col);
  }

  prevCells = cells.map((column) => [...column]);

  $("status").textContent = statusText();
  $("reset").hidden = myPlayer === null;

  const you = $("you");
  you.replaceChildren();
  if (myPlayer !== null) {
    const swatch = document.createElement("span");
    swatch.className = `swatch p${myPlayer}`;
    you.append(swatch, myPlayer === 1 ? "Вы играете красными" : "Вы играете жёлтыми");
  }
}

async function dropPiece(column) {
  if (!canMove()) return;
  $("game-error").textContent = "";

  try {
    state = await api("/api/move", {
      method: "POST",
      body: JSON.stringify({ column }),
    });
    render();
  } catch (err) {
    if (err.status === 401) return handleLoggedOut();
    $("game-error").textContent = err.message;
  }
}

$("reset").addEventListener("click", async () => {
  $("game-error").textContent = "";
  try {
    state = await api("/api/reset", { method: "POST" });
    prevCells = null;
    render();
  } catch (err) {
    if (err.status === 401) return handleLoggedOut();
    $("game-error").textContent = err.message;
  }
});

function handleLoggedOut() {
  me = null;
  const old = socket;
  socket = null;
  if (old) old.close();
  showAuth();
  $("auth-error").textContent = "Сессия закончилась. Войдите снова.";
}

(async function boot() {
  setAuthMode("login");
  try {
    me = await api("/api/auth/me");
    showGame();
    connect();
  } catch {
    showAuth();
  }
})();
