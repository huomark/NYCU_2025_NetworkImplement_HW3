from shared.protocol import *
from server.db_manager import DBManager
from server.game_manager import GameManager
import os
import shutil

class RequestHandler:
    def __init__(self, db_manager: DBManager, game_manager: GameManager):
        self.db = db_manager
        self.gm = game_manager
        self.sessions = {} # username -> socket

    def handle_request(self, request, client_socket):
        """
        Main dispatch entry point.
        request: dict
        client_socket: used for receiving files if needed (e.g. UPLOAD)
        Returns: response dict
        """
        cmd = request.get(FIELD_COMMAND)
        payload = request.get(FIELD_PAYLOAD, {})
        
        handler_map = {
            CMD_DEV_REGISTER: self.handle_dev_register,
            CMD_DEV_LOGIN: self.handle_dev_login,
            CMD_GAME_UPLOAD: self.handle_game_upload,
            CMD_GAME_LIST_MY: self.handle_game_list_my,
            CMD_GAME_UPDATE: self.handle_game_update,
            CMD_GAME_DELETE: self.handle_game_delete,
            
            CMD_PLAYER_REGISTER: self.handle_player_register,
            CMD_PLAYER_LOGIN: self.handle_player_login,
            CMD_STORE_LIST: self.handle_store_list,
            CMD_GAME_DETAIL: self.handle_game_detail,
            CMD_GAME_DOWNLOAD: self.handle_game_download,
            CMD_PLAYER_LIST: self.handle_player_list,
            CMD_ROOM_CREATE: self.handle_room_create,
            CMD_ROOM_LIST: self.handle_room_list,
            CMD_ROOM_JOIN: self.handle_room_join,
            CMD_GAME_START_NOTIFY: self.handle_game_start, # Host triggers start
            CMD_GAME_RATING: self.handle_game_rating
        }
        
        handler = handler_map.get(cmd)
        if handler:
            return handler(payload, client_socket)
        else:
            return {FIELD_STATUS: STATUS_ERROR, FIELD_MESSAGE: f"Unknown command: {cmd}"}

    def handle_disconnect(self, sock):
        """
        Called when a socket disconnects.
        Finds the associated user and cleans up.
        """
        disconnected_user = None
        # Find user by socket
        for user, s in list(self.sessions.items()):
            if s == sock:
                disconnected_user = user
                break
        
        if disconnected_user:
            del self.sessions[disconnected_user]
            print(f"User {disconnected_user} disconnected. Cleaning up...")
            self.gm.handle_player_disconnect(disconnected_user)

    # --- Developer Handlers ---
    def handle_dev_register(self, payload, sock):
        username = payload.get("username")
        password = payload.get("password")
        if self.db.register_user("developers", username, password):
            return {FIELD_STATUS: STATUS_OK, FIELD_MESSAGE: "Registered successfully"}
        return {FIELD_STATUS: STATUS_ERROR, FIELD_MESSAGE: "Username already exists"}

    def handle_dev_login(self, payload, sock):
        username = payload.get("username")
        password = payload.get("password")
        if self.db.validate_user("developers", username, password):
            return {FIELD_STATUS: STATUS_OK, FIELD_TOKEN: username} # simple token
        return {FIELD_STATUS: STATUS_ERROR, FIELD_MESSAGE: "Invalid credentials"}

    def handle_game_upload(self, payload, sock):
        # Multipart-like handling. Payload has metadata, socket stream has file.
        # But for simplicity, let's assume protocol: 
        # 1. Send JSON metadata (CMD_GAME_UPLOAD)
        # 2. Receive JSON response (Ready to receive?)
        # 3. Send Checksum or just raw bytes length prefixed?
        
        # Let's adjust: The request passed here is the JSON part.
        # We need to read the file content from 'sock' NOW.
        # Payload should contain 'file_size' and 'game_id' etc.
        
        username = payload.get("token") # check auth later properly
        game_meta = payload.get("game_meta")
        file_size = payload.get("file_size")
        
        if not username or not game_meta or not file_size:
            return {FIELD_STATUS: STATUS_ERROR, FIELD_MESSAGE: "Missing data"}

        # Read file stream
        # This blocks the selector thread, usually bad, but fine for this assignment scope.
        # Better: use a separate thread or non-blocking state machine. 
        # We'll use blocking recv for simplicity as per common HW patterns.
        
        import shared.utils as utils
        file_data = utils.recv_all(sock, file_size)
        
        if not file_data or len(file_data) != file_size:
             return {FIELD_STATUS: STATUS_ERROR, FIELD_MESSAGE: "File upload failed / incomplete"}

        # Save to temp, unzip, move.
        # Assume it's a ZIP or just storing raw bytes?
        # Prompt says "managed game space". Let's assume ZIP.
        
        game_id = game_meta["game_id"]
        target_dir = os.path.join("server_data", "games", game_id)
        
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir) # overwrite approach? Or update?
        os.makedirs(target_dir)
        
        zip_path = os.path.join(target_dir, "package.zip")
        with open(zip_path, "wb") as f:
            f.write(file_data)
            
        # Extract
        import zipfile
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            os.remove(zip_path) # clean up zip
        except Exception as e:
            return {FIELD_STATUS: STATUS_ERROR, FIELD_MESSAGE: f"Invalid Zip: {str(e)}"}
            
        # Update DB
        if self.db.add_game_update(username, game_meta):
            return {FIELD_STATUS: STATUS_OK, FIELD_MESSAGE: "Game uploaded"}
        return {FIELD_STATUS: STATUS_ERROR, FIELD_MESSAGE: "DB Update failed"}

    def handle_game_list_my(self, payload, sock):
        username = payload.get("token")
        all_games = self.db.get_all_games()
        my_games = [g for g in all_games if g.get("owner") == username]
        return {FIELD_STATUS: STATUS_OK, FIELD_PAYLOAD: my_games}

    def handle_game_update(self, payload, sock):
        # Similar to Upload but checking existence
        # For now, reuse upload logic if it overwrites.
        # But 'Update' might be just metadata update or code update.
        # Let's assume it calls upload logic.
        return {FIELD_STATUS: STATUS_ERROR, FIELD_MESSAGE: "Use Upload to update version"}

    def handle_game_delete(self, payload, sock):
        username = payload.get("token")
        game_id = payload.get("game_id")
        if self.db.delete_game(username, game_id):
            # Remove files
            path = os.path.join("server_data", "games", game_id)
            if os.path.exists(path):
                shutil.rmtree(path)
            return {FIELD_STATUS: STATUS_OK, FIELD_MESSAGE: "Deleted"}
        return {FIELD_STATUS: STATUS_ERROR, FIELD_MESSAGE: "Failed to delete"}

    # --- Player Handlers ---
    def handle_player_register(self, payload, sock):
        username = payload.get("username")
        password = payload.get("password")
        if self.db.register_user("players", username, password):
            return {FIELD_STATUS: STATUS_OK, FIELD_MESSAGE: "Registered successfully"}
        return {FIELD_STATUS: STATUS_ERROR, FIELD_MESSAGE: "Username already exists"}
        
    def handle_player_login(self, payload, sock):
        username = payload.get("username")
        password = payload.get("password")
        if self.db.validate_user("players", username, password):
            self.sessions[username] = sock # Track session
            return {FIELD_STATUS: STATUS_OK, FIELD_TOKEN: username}
        return {FIELD_STATUS: STATUS_ERROR, FIELD_MESSAGE: "Invalid credentials"}

    def handle_store_list(self, payload, sock):
        games = self.db.get_all_games()
        return {FIELD_STATUS: STATUS_OK, FIELD_PAYLOAD: games}

    def handle_player_list(self, payload, sock):
        # Return list of currently connected users (keys of self.sessions)
        online_users = list(self.sessions.keys())
        return {FIELD_STATUS: STATUS_OK, FIELD_PAYLOAD: online_users}

    def handle_game_detail(self, payload, sock):
        game_id = payload.get("game_id")
        game = self.db.get_game(game_id)
        if game:
            return {FIELD_STATUS: STATUS_OK, FIELD_PAYLOAD: game}
        return {FIELD_STATUS: STATUS_ERROR, FIELD_MESSAGE: "Game not found"}
        
    def handle_game_download(self, payload, sock):
        # Return file stream
        game_id = payload.get("game_id")
        # We need to zip the current server folder and send it.
        # Or if we kept the zip, send that. We deleted it.
        # Let's re-zip on demand or zip once.
        
        game_dir = os.path.join("server_data", "games", game_id)
        if not os.path.exists(game_dir):
            return {FIELD_STATUS: STATUS_ERROR, FIELD_MESSAGE: "Game files missing"}
            
        import zipfile, io
        
        # In memory zip
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(game_dir):
                for file in files:
                    abs_file = os.path.join(root, file)
                    rel_file = os.path.relpath(abs_file, game_dir)
                    zf.write(abs_file, rel_file)
        
        zip_data = mem_zip.getvalue()
        
        # Protocol: Send OK response with size, THEN send raw bytes
        # We need a special response flow here or modify `server.py` to handle raw sends.
        # The `handle_request` returns a dict. `DBManager` sends it.
        # We need to embed the file content? No, too big for JSON.
        # We can use a special status "FILE_STREAM_FOLLOWS".
        
        return {
            FIELD_STATUS: STATUS_OK, 
            "file_size": len(zip_data),
            "file_content_placeholder": "STREAM", # marker
            "_raw_data": zip_data # Hack: pass to server loop to send
        }

    def handle_room_create(self, payload, sock):
        host = payload.get("token")
        game_id = payload.get("game_id")
        # fetch game config from DB?
        game = self.db.get_game(game_id)
        if not game:
             return {FIELD_STATUS: STATUS_ERROR, FIELD_MESSAGE: "Game not found"}
            
        room_id = self.gm.create_room(host, game_id, game)
        return {FIELD_STATUS: STATUS_OK, FIELD_PAYLOAD: {"room_id": room_id}}

    def handle_room_list(self, payload, sock):
        rooms = self.gm.list_rooms()
        return {FIELD_STATUS: STATUS_OK, FIELD_PAYLOAD: rooms}

    def handle_room_join(self, payload, sock):
        player = payload.get("token")
        room_id = payload.get("room_id")
        success, msg = self.gm.join_room(room_id, player)
        if success:
            return {FIELD_STATUS: STATUS_OK, FIELD_MESSAGE: msg}
        return {FIELD_STATUS: STATUS_ERROR, FIELD_MESSAGE: msg}

    def handle_game_start(self, payload, sock):
        host = payload.get("token")
        room_id = payload.get("room_id")
        success, res = self.gm.start_game(room_id, host)
        if success:
            # Broadcast to all players in room
            # res is {"port": ..., "ip": ...}
            # We need room info to get player list
            # GameManager doesn't easily expose room object, let's fetch list
            # But list_rooms returns summary. 
            # We should probably access gm.rooms directly or add get_room_players method.
            # For speed, accessing private rooms or assumes I return players in start_game?
            # Let's use internal access for now or assume I can get it.
            room = self.gm.rooms.get(room_id)
            if room:
                for p in room.players:
                    if p != host: # Host gets return value
                        p_sock = self.sessions.get(p)
                        if p_sock:
                            try:
                                notify = {
                                    FIELD_COMMAND: "GAME_START",
                                    FIELD_PAYLOAD: res
                                }
                                import shared.utils as utils
                                utils.send_json(p_sock, notify)
                            except:
                                pass # socket dead?

            return {FIELD_STATUS: STATUS_OK, FIELD_PAYLOAD: res}
        return {FIELD_STATUS: STATUS_ERROR, FIELD_MESSAGE: res}

    def handle_game_rating(self, payload, sock):
        username = payload.get("token")
        game_id = payload.get("game_id")
        rating = payload.get("rating")
        comment = payload.get("comment")
        # Check if played? (Skip for now or check logs)
        if self.db.add_review(game_id, username, rating, comment):
            return {FIELD_STATUS: STATUS_OK, FIELD_MESSAGE: "Rated"}
        return {FIELD_STATUS: STATUS_ERROR, FIELD_MESSAGE: "Failed"}
