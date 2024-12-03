// Подключение к WebSocket-серверу
const socket = new WebSocket('ws://localhost:8765');

// Когда WebSocket открыт, логируем подключение
socket.addEventListener('open', function () {
    console.log('Connected to the WebSocket server');
});

// Когда WebSocket получает сообщение (игровой кадр)
socket.addEventListener('message', function (event) {
    const frame = event.data;
    console.log('Received frame:', frame);

    // Отображение игрового кадра или обновление доски
    const gameBoard = document.getElementById('game-board');
    gameBoard.textContent = frame; // Пример: отображение сырого кадра
});

// Обработка ошибок (например, если WebSocket неожиданно закроется)
socket.addEventListener('error', function (error) {
    console.error('WebSocket Error:', error);
});

// Когда WebSocket-соединение закрыто
socket.addEventListener('close', function () {
    console.log('WebSocket connection closed');
});

// Начало новой игры
startGame.addEventListener('click', function() {
    console.log('Starting new game...');
});