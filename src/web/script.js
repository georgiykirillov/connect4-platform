const playerId = getPlayerId();

const lobbyScreen = document.getElementById("lobby-screen");
const gameScreen = document.getElementById("game-screen");

const usernameInput = document.getElementById("username");
const createButton = document.getElementById("create-table");
const refreshButton = document.getElementById("refresh-tables");
const tablesList = document.getElementById("tables-list");

const tableNameElement = document.getElementById("table-name");
const tableCodeElement = document.getElementById("table-code");
const statusElement = document.getElementById("status");
const boardElement = document.getElementById("board");

const playerOneElement = document.getElementById("player-one-name");
const playerTwoElement = document.getElementById("player-two-name");

const lobbyError = document.getElementById("lobby-error");
const gameError = document.getElementById("game-error");
const backButton = document.getElementById("back-to-lobby");

usernameInput.value = localStorage.getItem("connect4-username") || "";

let currentTable = null;
let currentTableId = null;
let myPlayer = null;
let lastState = null;
let socket = null;
let reconnectTimer = null;
let busy = false;
let intentionalClose = false;


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


function getUsername() {
    const username = usernameInput.value.trim();

    if (!username) {
        throw new Error("Введи своё имя.");
    }

    localStorage.setItem("connect4-username", username);

    return username;
}


function showError(element, message) {
    element.textContent = message || "";
}


function showLobby() {
    intentionalClose = true;

    if (socket) {
        socket.close();
        socket = null;
    }

    if (reconnectTimer !== null) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }

    currentTable = null;
    currentTableId = null;
    myPlayer = null;
    lastState = null;
    busy = false;

    history.replaceState(null, "", "/");

    lobbyScreen.hidden = false;
    gameScreen.hidden = true;

    showError(gameError, "");
    loadTables();
}


function showGame() {
    lobbyScreen.hidden = true;
    gameScreen.hidden = false;
}


function renderTables(tables) {
    tablesList.replaceChildren();

    if (tables.length === 0) {
        const empty = document.createElement("p");
        empty.className = "description";
        empty.textContent = "Пока нет открытых столов. Создай первый!";
        tablesList.appendChild(empty);
        return;
    }

    for (const table of tables) {
        const card = document.createElement("div");
        card.className = "table-card";

        const info = document.createElement("div");

        const name = document.createElement("h3");
        name.textContent = table.name;

        const description = document.createElement("p");
        description.textContent = "Ожидает второго игрока";

        info.append(name, description);

        const button = document.createElement("button");
        button.className = "secondary-button";
        button.textContent = "Войти";
        button.type = "button";

        button.addEventListener("click", () => {
            joinTable(table.table_id, button);
        });

        card.append(info, button);
        tablesList.appendChild(card);
    }
}


async function loadTables() {
    showError(lobbyError, "");

    try {
        const tables = await request("/api/tables");
        renderTables(tables);
    } catch (error) {
        showError(lobbyError, error.message);
    }
}


async function createTable() {
    createButton.disabled = true;
    showError(lobbyError, "");

    try {
        const username = getUsername();

        const table = await request("/api/tables", {
            method: "POST",
            body: JSON.stringify({
                player_id: playerId,
                username,
            }),
        });

        await enterTable(table.table_id);
    } catch (error) {
        showError(lobbyError, error.message);
    } finally {
        createButton.disabled = false;
    }
}


async function joinTable(tableId, button) {
    button.disabled = true;
    showError(lobbyError, "");

    try {
        const username = getUsername();

        await request(`/api/tables/${tableId}/join`, {
            method: "POST",
            body: JSON.stringify({
                player_id: playerId,
                username,
            }),
        });

        await enterTable(tableId);
    } catch (error) {
        showError(lobbyError, error.message);
        await loadTables();
    }
}


async function enterTable(tableId) {
    const table = await request(`/api/tables/${tableId}`);

    const isHost = table.host.id === playerId;
    const isGuest = table.guest?.id === playerId;

    if (!isHost && !isGuest) {
        throw new Error("Ты не являешься участником этого стола.");
    }

    intentionalClose = true;

    if (socket) {
        socket.close();
        socket = null;
    }

    if (reconnectTimer !== null) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }

    currentTable = table;
    currentTableId = tableId;
    myPlayer = null;
    lastState = table.state;

    history.replaceState(
        null,
        "",
        `/?table_id=${encodeURIComponent(tableId)}`
    );

    showGame();

    tableNameElement.textContent = table.name;
    tableCodeElement.textContent = `Код стола: ${tableId}`;

    render(lastState);
    intentionalClose = false;
    connect();
}


function getPlayerName(number) {
    if (!currentTable) {
        return `Игрок ${number}`;
    }

    const ownPlayer = currentTable.host.id === playerId
        ? currentTable.host
        : currentTable.guest;

    const opponent = currentTable.host.id === playerId
        ? currentTable.guest
        : currentTable.host;

    if (myPlayer === number) {
        return ownPlayer?.username || `Игрок ${number} (ты)`;
    }

    return opponent?.username || `Ожидаем игрока ${number}`;
}


function render(state) {
    lastState = state;

    const { game, board } = state;

    playerOneElement.textContent = getPlayerName(1);
    playerTwoElement.textContent = getPlayerName(2);

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

    if (game.status === "waiting") {
        statusElement.textContent = "Ожидаем второго игрока...";
    } else if (game.status === "finished") {
        statusElement.textContent = `Победил ${getPlayerName(game.winner)}!`;
    } else if (game.status === "draw") {
        statusElement.textContent = "Ничья!";
    } else if (myPlayer === null) {
        statusElement.textContent = "Подключаемся к игре...";
    } else if (game.current_player === myPlayer) {
        statusElement.textContent = "Твой ход!";
    } else {
        statusElement.textContent =
            `Ход ${getPlayerName(game.current_player)}`;
    }
}


async function play(column) {
    if (
        busy ||
        !lastState ||
        myPlayer === null ||
        lastState.game.current_player !== myPlayer
    ) {
        return;
    }

    busy = true;
    render(lastState);
    showError(gameError, "");

    try {
        const state = await request(
            `/api/tables/${currentTableId}/move`,
            {
                method: "POST",
                body: JSON.stringify({
                    player_id: playerId,
                    column,
                }),
            }
        );

        render(state);
    } catch (error) {
        showError(gameError, error.message);
    } finally {
        busy = false;

        if (lastState) {
            render(lastState);
        }
    }
}


async function updateTableInfo() {
    if (!currentTableId) return;

    try {
        const table = await request(
            `/api/tables/${currentTableId}`
        );

        if (table.table_id !== currentTableId) return;

        currentTable = table;
        tableNameElement.textContent = table.name;

        render(lastState);
    } catch (error) {
        showError(gameError, error.message);
    }
}


function connect() {
    if (!currentTableId || intentionalClose) return;

    if (
        socket &&
        (socket.readyState === WebSocket.CONNECTING ||
         socket.readyState === WebSocket.OPEN)
    ) {
        return;
    }

    const protocol = location.protocol === "https:" ? "wss:" : "ws:";

    socket = new WebSocket(
        `${protocol}//${location.host}/ws/table/${encodeURIComponent(currentTableId)}?player_id=${encodeURIComponent(playerId)}`
    );

    socket.onopen = () => {
        showError(gameError, "");
    };

    socket.onmessage = async (event) => {
        try {
            const message = JSON.parse(event.data);

            if (message.type === "init" || message.type === "state") {
                myPlayer = message.player;
                render(message.state);

                await updateTableInfo();
            }
        } catch (error) {
            showError(gameError, "Не удалось обработать ответ сервера.");
            console.error(error);
        }
    };

    socket.onerror = () => {
        statusElement.textContent = "Ошибка подключения к серверу";
    };

    socket.onclose = () => {
        if (intentionalClose) return;

        myPlayer = null;

        if (lastState) {
            render(lastState);
        }

        statusElement.textContent = "Связь потеряна. Подключаемся...";

        if (reconnectTimer !== null) {
            clearTimeout(reconnectTimer);
        }

        reconnectTimer = setTimeout(() => {
            reconnectTimer = null;
            connect();
        }, 1500);
    };
}


createButton.addEventListener("click", createTable);

refreshButton.addEventListener("click", loadTables);

backButton.addEventListener("click", showLobby);


async function initialize() {
    const params = new URLSearchParams(location.search);
    const tableId = params.get("table_id");

    if (tableId) {
        try {
            await enterTable(tableId);
        } catch (error) {
            showError(lobbyError, error.message);
            showLobby();
        }
    } else {
        await loadTables();
    }
}


initialize();
