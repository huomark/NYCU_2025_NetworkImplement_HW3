# Game Store System (HW3)

## Overview
A multiplayer game store and lobby system supporting Developer and Player roles.
- **Server**: Central hub for authentication, store management, and room hosting.
- **Developer Client**: CLI for uploading and managing games.
- **Player Client**: CLI for browsing the store, downloading games, and playing in rooms.

## Requirements
- Python 3.8+
- Windows (as tested) or Linux

## Quick Start

### 1. Start Support Infrastructure
First, ensure you have the project folder structure.
```
hw3/
  server/
  developer/
  player/
  shared/
  games/
```

### 2. Start the Server
Run the Main Server. This must differ from Game Servers.
```bash
python -m server.server
```
*The server listens on 0.0.0.0:8888 by default.*

### 3. Developer Workflow (Upload a Game)
1. Open a new terminal.
2. Run Developer Client:
   ```bash
   python developer/developer.py
   ```
3. Register a new account (Option 1).
4. Login (Option 2).
5. Upload a Game (Option 2).
   - Use default path `games/template` for a test game.
   - The game "Template Game" will be uploaded.

### 4. Player Workflow (Play the Game)
1. Open a new terminal (Player 1).
2. Run Player Client:
   ```bash
   python player/player.py
   ```
3. Register/Login.
4. **Store**: Go to Store (1), select "Template Game", and **Download** it.
5. **Rooms**: Create a Room (2) with "template_game".
   - You are now Host. Waiting for start.
   
6. (Optional) Open another terminal (Player 2).
   - Run Player Client, Login.
   - Download "Template Game".
   - Go to Rooms, **Join** the existing room.

7. **Start Game**:
   - Player 1 (Host) presses 's'.
   - The Server launches the Game Server process.
   - Both Clients automatically launch the Game Client subprocess.
   - You should see the Game Window/Console appear.

## Project Structure
- `server/`: Server logic (DB, Lobby, Game Manager).
- `developer/`: Developer tools.
- `player/`: Player tools and UI.
- `shared/`: Common protocol and utilities.
- `games/`: Source code for games (Template included).

## Architecture
- **Communication**: JSON-based custom protocol over TCP.
- **Game Execution**: Games are uploaded as ZIPs, distributed to Players, and executed as independent subprocesses. The configuration `config.json` determines entry points.
- **Networking**: One Main Server handles Lobby/Store. Dynamic ports are assigned for Game Servers.
