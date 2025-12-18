import json
import os
import threading

class DBManager:
    def __init__(self, data_dir="server_data"):
        self.data_dir = data_dir
        self.users_file = os.path.join(data_dir, "users.json")
        self.games_file = os.path.join(data_dir, "games.json")
        self.lock = threading.RLock()
        
        self._ensure_dir()
        self.users = self._load_json(self.users_file, {"developers": {}, "players": {}})
        self.games = self._load_json(self.games_file, {})

    def _ensure_dir(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def _load_json(self, filepath, default):
        if not os.path.exists(filepath):
            return default
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default

    def _save_json(self, filepath, data):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def save_all(self):
        with self.lock:
            self._save_json(self.users_file, self.users)
            self._save_json(self.games_file, self.games)

    # --- User Management ---
    def register_user(self, user_type, username, password):
        """user_type: 'developers' or 'players'"""
        with self.lock:
            if username in self.users[user_type]:
                return False
            self.users[user_type][username] = {"password": password, "games": []} # games owned or library
            self.save_all()
            return True

    def validate_user(self, user_type, username, password):
        with self.lock:
            if username not in self.users[user_type]:
                return False
            return self.users[user_type][username]["password"] == password

    # --- Game Management ---
    def add_game_update(self, dev_username, game_meta):
        """
        game_meta: {game_id, name, version, description, type, ...}
        """
        with self.lock:
            game_id = game_meta["game_id"]
            
            # If new game, developer owns it
            if game_id not in self.games:
                 # Check if dev already owns it or it's new
                 self.games[game_id] = game_meta
                 self.games[game_id]["owner"] = dev_username
                 self.games[game_id]["reviews"] = []
                 self.games[game_id]["versions"] = [game_meta["version"]]
            else:
                # Update existing
                if self.games[game_id]["owner"] != dev_username:
                    return False # Not owner
                # Update fields
                self.games[game_id].update(game_meta)
                if game_meta["version"] not in self.games[game_id]["versions"]:
                    self.games[game_id]["versions"].append(game_meta["version"])
            
            self.save_all()
            return True

    def get_all_games(self):
        with self.lock:
            return list(self.games.values())

    def get_game(self, game_id):
        with self.lock:
            return self.games.get(game_id)
            
    def delete_game(self, dev_username, game_id):
        with self.lock:
            if game_id in self.games and self.games[game_id]["owner"] == dev_username:
                del self.games[game_id]
                self.save_all()
                return True
            return False

    def add_review(self, game_id, username, rating, comment):
        with self.lock:
            if game_id in self.games:
                review = {"user": username, "rating": rating, "comment": comment}
                self.games[game_id].setdefault("reviews", []).append(review)
                self.save_all()
                return True
            return False
