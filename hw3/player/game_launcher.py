import subprocess
import os
import json
import sys

class GameLauncher:
    def __init__(self, downloads_dir="downloads"):
        self.downloads_dir = downloads_dir

    def launch(self, user_downloads_dir, game_id, ip, port, username):
        """
        Launches the game client.
        user_downloads_dir: path like "player/downloads/Player1"
        """
        game_path = os.path.join(user_downloads_dir, game_id)
        if not os.path.exists(game_path):
            print(f"Game files not found at {game_path}")
            return False

        config_path = os.path.join(game_path, "config.json")
        if not os.path.exists(config_path):
            print("config.json missing")
            return False

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except:
            print("Invalid config")
            return False

        entry = config.get("client_entry_point", "client.py")
        script_path = os.path.join(game_path, entry)
        
        if not os.path.exists(script_path):
            print(f"Client entry point {entry} not found")
            return False
            
        print(f"Launching {game_id}...")
        # New console for game client
        cmd = [sys.executable, script_path, ip, str(port), username]
        
        try:
            # Creation flags for separate window on Windows
            creationflags = subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            subprocess.Popen(cmd, cwd=game_path, creationflags=creationflags)
            return True
        except Exception as e:
            print(f"Failed to launch: {e}")
            return False
