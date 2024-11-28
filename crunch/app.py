import asyncio
import websockets
from flask import Flask, render_template
from chess import Game
import threading

app = Flask(__name__)


# WebSocket server
async def server(websocket, path=None):
    try:
        game = Game()  # Create a new game instance
        while True:
            frame = game.render_frame()  # Assuming this returns some kind of game frame
            await websocket.send(frame.read())  # Send the game frame to the client
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")


async def start_server():
    return await websockets.serve(server, "localhost", 8765)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/game')
def game():
    return render_template('game.html')


@app.route('/puzzles')
def puzzles():
    return render_template('puzzles.html')


def run_websocket():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_server())
    loop.run_forever()


if __name__ == '__main__':
    websocket_thread = threading.Thread(target=run_websocket)
    websocket_thread.start()

    app.run(debug=True)
