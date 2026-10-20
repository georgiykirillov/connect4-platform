const boardElement = document.getElementById("board");
const statusElement = document.getElementById("status");
const errorElement = document.getElementById("error");
const resetButton = document.getElementById("reset");

function getPlayerId() {
    let id = localStorage.getItem("connect4-player-id");

    if (!id) {
        if (typeof crypto.randomUUID === "function") {
            id = crypto.randomUUID();
        } else {
            id = `player-${Date.now()}-${Math.random().toString(36).slice(2)}`;
        }

        localStorage.setItem("connect4-player-id", id);
    }

    return id;
}

const playerId = getPlayerId();

let busy = false;
let lastState = null;
let myPlayer = null;
let socket = null;
let reconnectTimer = null;

async function request(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...options.headers,
        },
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || "Не удалось выполнить запрос.");
    }

    return data;
}

function showError(message) {
    if (errorElement) {
        errorElement.textContent = message;
    } else if (message) {
        console.error(message);
    }
}

function render(state) {
    lastState = state;

    const { game, board } = state;
    boardElement.replaceChildren();

    for (let x = 0; x < board.width; x++) {
        const column = document.createElement("button");

        column.type = "button";
        column.className = "column";
        column.disabled =
            busy ||
            myPlayer === null ||
            game.status !== "in_progress" ||
            game.current_player !== myPlayer;

        column.setAttribute("aria-label", `Колонка ${x + 1}`);

        // Движок хранит клетки по колонкам, API отдаёт строки сверху вниз.
        // Рисуем снизу вверх, чтобы фишки оказывались внизу.
        for (let y = board.height - 1; y >= 0; y--) {
            const cell = document.createElement("span");
            const value = board.cells[y][x];

            cell.className = "cell";

            if (value === 1) {
                cell.classList.add("p1");
            } else if (value === 2) {
                cell.classList.add("p2");
            } else {
                cell.classList.add("empty");
            }

            column.appendChild(cell);
        }

        column.addEventListener("click", () => play(x));
        boardElement.appendChild(column);
    }

    if (game.status === "finished") {
        statusElement.textContent = `Победил игрок ${game.winner}!`;
    } else if (game.status === "draw") {
        statusElement.textContent = "Ничья!";
    } else if (myPlayer === null) {
        statusElement.textContent = "Ты наблюдатель — оба места заняты";
    } else if (game.current_player === myPlayer) {
        statusElement.textContent = `Твой ход! Ты — игрок ${myPlayer}`;
    } else {
        statusElement.textContent =
            `Ход игрока ${game.current_player} · Ты — игрок ${myPlayer}`;
    }

    resetButton.disabled = busy || myPlayer !== 1;
}

async function run(action) {
    if (busy) return;

    busy = true;
    showError("");

    if (lastState) {
        render(lastState);
    }

    try {
        const state = await action();
        render(state);
    } catch (error) {
        showError(error.message);
    } finally {
        busy = false;

        if (lastState) {
            render(lastState);
        }
    }
}

function play(column) {
    if (
        busy ||
        !lastState ||
        myPlayer === null ||
        lastState.game.current_player !== myPlayer
    ) {
        return;
    }

    return run(() => request("/api/move", {
        method: "POST",
        body: JSON.stringify({
            column,
            game_id: "main",
            player_id: playerId,
        }),
    }));
}

resetButton.addEventListener("click", () => {
    if (myPlayer !== 1) return;

    run(() => request("/api/reset", {
        method: "POST",
        body: JSON.stringify({
            player_id: playerId,
        }),
    }));
});

function connect() {
    if (
        socket &&
        (socket.readyState === WebSocket.CONNECTING ||
         socket.readyState === WebSocket.OPEN)
    ) {
        return;
    }

    const protocol = location.protocol === "https:" ? "wss:" : "ws:";

    socket = new WebSocket(
        `${protocol}//${location.host}/ws?player_id=${encodeURIComponent(playerId)}`
    );

    socket.onopen = () => {
        showError("");
    };

    socket.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);

            if (message.type === "init") {
                myPlayer = message.player;
                render(message.state);
            } else if (message.type === "state") {
                myPlayer = message.player;
                render(message.state);
            }
        } catch (error) {
            showError("Не удалось обработать ответ сервера.");
            console.error(error);
        }
    };

    socket.onerror = () => {
        statusElement.textContent = "Ошибка подключения к серверу";
    };

    socket.onclose = () => {
        myPlayer = null;

        if (lastState) {
            render(lastState);
        } else {
            statusElement.textContent = "Связь потеряна. Подключаемся...";
        }

        if (reconnectTimer !== null) {
            clearTimeout(reconnectTimer);
        }

        reconnectTimer = setTimeout(() => {
            reconnectTimer = null;
            connect();
        }, 1500);
    };
}

connect();
