// Connect to the WebSocket server
const socket = new WebSocket('ws://localhost:8765');

// When the WebSocket is open, log the connection
socket.onopen = () => {
    console.log('Connected to the WebSocket server');
};

// When the WebSocket receives a message (a game frame)
socket.onmessage = (event) => {
    const frame = event.data;
    console.log('Received frame:', frame);

    // Display the game frame or update the board here
    const gameBoard = document.getElementById('game-board');
    gameBoard.textContent = frame;  // Example: display raw frame for now
};

// Handle errors (e.g., if the WebSocket closes unexpectedly)
socket.onerror = (error) => {
    console.error('WebSocket Error:', error);
};

// When the WebSocket connection is closed
socket.onclose = () => {
    console.log('WebSocket connection closed');
};

// Function to start a new game (could send a message to the server if needed)
function startGame() {
    console.log('Starting new game...');
    // You can send a message to the server to start the game if necessary
    socket.send('start_game');
}