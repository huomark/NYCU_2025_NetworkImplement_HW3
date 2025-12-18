import subprocess
import threading
import sys
import socket
import time
import os

class Room:
    def __init__(self, room_id, host, game_id, game_config):
        self.room_id = room_id
        self.host = host
        self.game_id = game_id
        self.players = [host]
        self.status = "WAITING" # WAITING, PLAYING
        self.port = None
        self.process = None
        self.game_config = game_config

class GameManager:
    def __init__(self, port_start=9000, port_end=9100):
        self.rooms = {}
        self.lock = threading.Lock()
        self.port_start = port_start
        self.port_end = port_end
        self.used_ports = set()
        self.next_room_id = 1

    def create_room(self, host, game_id, game_config):
        with self.lock:
            room_id = str(self.next_room_id)
            self.next_room_id += 1
            room = Room(room_id, host, game_id, game_config)
            self.rooms[room_id] = room
            return room_id

    def list_rooms(self):
        with self.lock:
            return [
                {
                    "id": r.room_id, 
                    "game_id": r.game_id, 
                    "host": r.host, 
                    "players": len(r.players),
                    "status": r.status
                }
                for r in self.rooms.values()
            ]

    def join_room(self, room_id, player):
        with self.lock:
            if room_id not in self.rooms:
                return False, "Room not found"
            room = self.rooms[room_id]
            if room.status != "WAITING":
                return False, "Game already started"
            # Limit players check? (Optional, based on game_config)
            room.players.append(player)
            return True, "Joined"

    def start_game(self, room_id, user):
        """
        Only host can start.
        Allocates a port, starts the subprocess.
        """
        with self.lock:
            if room_id not in self.rooms:
                return False, "Room not found"
            room = self.rooms[room_id]
            if room.host != user:
                return False, "Only host can start"
            
            # Allocate port
            port = self._get_free_port()
            if not port:
                return False, "No server ports available"
            
            room.port = port
            room.status = "PLAYING"
            
            # Launch Subprocess
            # Command should be: python server_data/games/<game_id>/server.py <port> <num_players> ...
            # We need to trust the setup. For now, assume consistent structure.
            # However, looking at requirements, Developer uploads a zip. Server extracts it.
            # We assume a standard entry point, e.g., 'server.py' or specified in config.
            
            game_dir = os.path.abspath(os.path.join("server_data", "games", room.game_id))
            # Find entry point from config or default
            # For simplicity, we assume 'server.py' exists in the game root.
            
            script_path = os.path.join(game_dir, "server.py")
            if not os.path.exists(script_path):
                return False, f"Game server script not found: {script_path}"

            # Run in new process
            # Pass arguments: port
            cmd = [sys.executable, script_path, str(port)]
            
            try:
                # We use creationflags=subprocess.CREATE_NEW_CONSOLE to let it pop up separately (easy for demo)
                # Or just running in background.
                # For demo visualization, separate console is nice, but headless is safer if linux.
                # Prompt says: "Server... deployed on Linux". HW2 environment.
                # So we can't use CREATE_NEW_CONSOLE.
                
                # room.process = subprocess.Popen(cmd, cwd=game_dir)
                room.process = subprocess.Popen(cmd, cwd=game_dir)
                
                # Get actual LAN IP to return to clients
                try:
                    # Trick to get IP that's connected to internet/network
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    host_ip = s.getsockname()[0]
                    s.close()
                except:
                    host_ip = "127.0.0.1"
                
                return True, {"port": port, "ip": host_ip} # Return IP/Port to clients
            except Exception as e:
                return False, str(e)

    def _get_free_port(self):
        for p in range(self.port_start, self.port_end):
            if p not in self.used_ports:
                # Double check if actually free
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    if s.connect_ex(('localhost', p)) != 0:
                        self.used_ports.add(p)
                        return p
        return None
        
    def end_game(self, room_id):
        with self.lock:
            if room_id in self.rooms:
                room = self.rooms[room_id]
                if room.process:
                    room.process.terminate()
                if room.port:
                    self.used_ports.discard(room.port)
                del self.rooms[room_id]

    def handle_player_disconnect(self, username):
        with self.lock:
            # Find rooms where user is host or player
            rooms_to_destroy = []
            
            for room_id, room in self.rooms.items():
                if room.host == username:
                    rooms_to_destroy.append(room_id)
                elif username in room.players:
                    room.players.remove(username)
            
            for rid in rooms_to_destroy:
                self.end_game(rid)

