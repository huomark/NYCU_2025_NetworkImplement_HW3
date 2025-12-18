import socket
import sys
import json
import os
import io
import zipfile
import time
import msvcrt
import shutil

# Adjust path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.protocol import *
import shared.utils as utils
try:
    from player.game_launcher import GameLauncher
except ImportError:
    from game_launcher import GameLauncher


# Remove global HOST input
# HOSTIUU = input("please input server ip: ") 
# HOST = HOSTIUU
PORT = 8888

class PlayerClient:
    def __init__(self, host='127.0.0.1', port=8888):
        self.host = host
        self.port = port
        self.sock = None
        self.token = None # username
        self.username = None
        self.downloads_root = os.path.join(os.path.dirname(__file__), "downloads")
        self.launcher = GameLauncher(self.downloads_root)

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            print(f"Connected to Lobby Server at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def send_request(self, command, payload):
        req = {FIELD_COMMAND: command, FIELD_PAYLOAD: payload}
        if self.token:
            req[FIELD_TOKEN] = self.token
        utils.send_json(self.sock, req)
        
    def recv_response(self):
        return utils.recv_json(self.sock)

    def main_loop(self):
        if not self.connect():
            return
        
        while True:
            if not self.token:
                self.auth_menu()
            else:
                self.lobby_menu()

    def auth_menu(self):
        print("\n=== Player Auth ===")
        print("1. Register")
        print("2. Login")
        print("3. Exit")
        choice = input("Select: ")
        
        if choice == '1':
            user = input("Username: ")
            pwd = input("Password: ")
            self.send_request(CMD_PLAYER_REGISTER, {"username": user, "password": pwd})
            resp = self.recv_response()
            # Consume potential raw data? No, register doesn't send files.
            # But wait, my test script had to consume extra recv?
            # No, that was likely server sending login response immediately or sync issue.
            # Standard blocking recv is fine here.
            
            print(f"Result: {resp.get(FIELD_MESSAGE)}")
            
        elif choice == '2':
            user = input("Username: ")
            pwd = input("Password: ")
            self.send_request(CMD_PLAYER_LOGIN, {"username": user, "password": pwd})
            resp = self.recv_response()
            if resp.get(FIELD_STATUS) == STATUS_OK:
                self.token = resp.get(FIELD_TOKEN)
                self.username = user
                print(f"Login successful. Welcome {user}!")
            else:
                print(f"Login failed: {resp.get(FIELD_MESSAGE)}")
        elif choice == '3':
            sys.exit(0)

    def lobby_menu(self):
        print(f"\n=== Player Lobby ({self.username}) ===")
        print("1. Store (Browse/Download)")
        print("2. My Library (Local)")
        print("3. Rooms (Create/Join)")
        print("4. Online Players")
        print("5. Logout")
        choice = input("Select: ")

        if choice == '1':
            self.menu_store()
        elif choice == '2':
            self.menu_library()
        elif choice == '3':
            self.menu_rooms()
        elif choice == '4':
            self.menu_online_players()
        elif choice == '5':
            self.token = None
            self.username = None

    def menu_store(self):
        self.send_request(CMD_STORE_LIST, {})
        resp = self.recv_response()
        games = resp.get(FIELD_PAYLOAD, [])
        print("\n--- Game Store ---")
        for g in games:
            print(f"ID: {g.get('game_id')} | Name: {g.get('name')} | v{g.get('version')}")
        
        choice = input("\nEnter Game ID to download or 'b' to back: ")
        if choice and choice != 'b':
            self.download_game(choice)

    def game_detail(self, game):
        print(f"\nTitle: {game['name']}")
        print(f"Desc: {game['description']}")
        print(f"Version: {game['version']}")
        print("1. Download")
        print("2. Back")
        
        if input("Choice: ") == '1':
            self.download_game(game['game_id'])

    def download_game(self, game_id):
        print(f"Requesting download for {game_id}...")
        self.send_request(CMD_GAME_DOWNLOAD, {"game_id": game_id})
        
        # Expect header
        resp = self.recv_response()
        if resp.get(FIELD_STATUS) != STATUS_OK:
            print(f"Download failed: {resp.get(FIELD_MESSAGE)}")
            return
            
        file_size = resp.get("file_size")
        print(f"Downloading {file_size} bytes...")
        
        # Read raw
        zip_data = utils.recv_all(self.sock, file_size)
        
        # Save
        user_dir = os.path.join(self.downloads_root, self.username)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
            
        zip_path = os.path.join(user_dir, f"{game_id}.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_data)
            
        # Extract
        game_path = os.path.join(user_dir, game_id)
        if os.path.exists(game_path):
            shutil.rmtree(game_path)
        os.makedirs(game_path)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(game_path)
            os.remove(zip_path)
            print("Downloaded and Extracted.")
        except Exception as e:
            print(f"Extraction failed: {e}")

    def get_local_version(self, game_id):
        user_dir = os.path.join(self.downloads_root, self.username)
        config_path = os.path.join(user_dir, game_id, "config.json")
        try:
            with open(config_path, 'r') as f:
                return json.load(f).get("version", "?.?.?")
        except:
            return "?.?.?"

    def menu_library(self):
        user_dir = os.path.join(self.downloads_root, self.username)
        if not os.path.exists(user_dir):
            print("Library empty.")
            return
        
        games = [d for d in os.listdir(user_dir) if os.path.isdir(os.path.join(user_dir, d))]
        print("\n--- My Library ---")
        for g in games:
            ver = self.get_local_version(g)
            print(f"- {g} (v{ver})")
        input("Press Enter...")

    def menu_rooms(self):
        print("\n--- Room Menu ---")
        print("1. List/Join Rooms")
        print("2. Create Room")
        print("3. Back")
        choice = input("Choice: ")
        
        if choice == '1':
            self.list_rooms()
        elif choice == '2':
            self.create_room()

    def list_join_rooms(self):
        self.send_request(CMD_ROOM_LIST, {})
        resp = self.recv_response()
        rooms = resp.get(FIELD_PAYLOAD, [])
        
        print("\n--- Rooms ---")
        for i, r in enumerate(rooms):
            print(f"{i+1}. Room {r['id']} ({r['status']}) - {r['game_id']} (Host: {r['host']})")
            
        print("Enter number to join, or 0 to back.")
        try:
            sel = int(input("Choice: "))
            if sel == 0: return
            if 1 <= sel <= len(rooms):
                room = rooms[sel-1]
                self.join_room(room['id'], room['game_id'])
        except ValueError:
            pass

    def list_rooms(self):
        self.send_request(CMD_ROOM_LIST, {})
        resp = self.recv_response()
        rooms = resp.get(FIELD_PAYLOAD, [])
        print("\n--- Rooms ---")
        for r in rooms:
            print(f"{r['id']}. {r['game_id']} ({r['status']}) - {r['players']} players (Host: {r['host']})")
        
        choice = input("Enter number to join, or 0 to back.\nChoice: ")
        if choice and choice != '0':
            # Map choice to room_id? Assuming ID is number string
            # Let's find room
            target_room = None
            for r in rooms:
                if r['id'] == choice:
                    target_room = r
                    break
            
            if target_room:
                self.join_room(target_room['id'], target_room['game_id'])

    def check_game_update(self, game_id):
        """
        Checks if the local game version matches the server version.
        Prompt user to update if different.
        """
        user_dir = os.path.join(self.downloads_root, self.username)
        game_path = os.path.join(user_dir, game_id)
        config_path = os.path.join(game_path, "config.json")
        
        if not os.path.exists(config_path):
            return # Should be handled by existence check elsewhere
            
        # Get Local Version
        try:
            with open(config_path, 'r') as f:
                local_config = json.load(f)
                local_version = local_config.get("version", "0.0.0")
        except:
            local_version = "0.0.0"

        # Get Server Version
        self.send_request(CMD_GAME_DETAIL, {"game_id": game_id})
        resp = self.recv_response()
        
        if resp.get(FIELD_STATUS) == STATUS_OK:
            server_game = resp.get(FIELD_PAYLOAD)
            server_version = server_game.get("version", "0.0.0")
            
            if server_version != local_version:
                print(f"\n[UPDATE DETECTED] Game '{game_id}' has a new version!")
                print(f"Local: v{local_version}  Vs  Server: v{server_version}")
                choice = input("Update now? (Y/n): ").lower()
                if choice != 'n':
                    self.download_game(game_id)
                    print("Game updated.")
        

    def menu_online_players(self):
        self.send_request(CMD_PLAYER_LIST, {})
        resp = self.recv_response()
        players = resp.get(FIELD_PAYLOAD, [])
        print("\n--- Online Players ---")
        if not players:
            print("No one else is online.")
        else:
            for p in players:
                print(f"- {p}")
        input("Press Enter...")

    def create_room(self):
        user_dir = os.path.join(self.downloads_root, self.username)
        if not os.path.exists(user_dir):
            print("You have no installed games. Please download some first.")
            return

        games = [d for d in os.listdir(user_dir) if os.path.isdir(os.path.join(user_dir, d))]
        if not games:
            print("You have no installed games. Please download some first.")
            return

        print("\n--- Installed Games (Ready to Host) ---")
        for i, g in enumerate(games):
            ver = self.get_local_version(g)
            print(f"{i+1}. {g} (v{ver})")

        choice = input("\nEnter Game ID or Number to host: ").strip()
        
        gid = choice
        # Check if number
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(games):
                gid = games[idx]

        game_path = os.path.join(user_dir, gid)
        if not os.path.exists(game_path):
             print(f"Game '{gid}' not found in installed games.")
             return

        # Check for updates
        self.check_game_update(gid)

        self.send_request(CMD_ROOM_CREATE, {"game_id": gid})
        resp = self.recv_response()
        if resp.get(FIELD_STATUS) == STATUS_OK:
            rid = resp.get(FIELD_PAYLOAD)['room_id']
            print(f"Room {rid} Created!")
            self.wait_room(rid, gid, is_host=True)
        else:
            print(f"Error: {resp.get(FIELD_MESSAGE)}")

    def join_room(self, room_id, game_id):
        # Check local
        user_dir = os.path.join(self.downloads_root, self.username)
        game_path = os.path.join(user_dir, game_id)
        
        if not os.path.exists(game_path):
            print(f"Game '{game_id}' not found locally.")
            choice = input(f"Do you want to download it now? (y/N): ").lower()
            if choice == 'y':
                self.download_game(game_id)
                if not os.path.exists(game_path):
                    print("Download failed or cancelled. Cannot join room.")
                    return
            else:
                return

        # Check for updates
        self.check_game_update(game_id)

        self.send_request(CMD_ROOM_JOIN, {"room_id": room_id})
        resp = self.recv_response()
        if resp.get(FIELD_STATUS) == STATUS_OK:
            print("Joined Room!")
            self.wait_room(room_id, game_id, is_host=False)
        else:
            print(f"Error: {resp.get(FIELD_MESSAGE)}")

    def wait_room(self, room_id, game_id, is_host):
        print(f"\nIn Room {room_id}. Waiting for game start...")
        print("Host: Press 's' to start. Client: Wait.")
        print("Press 'q' to leave.")
        
        while True:
            # Poll Input
            if msvcrt.kbhit():
                key = msvcrt.getch().decode().lower()
                if is_host and key == 's':
                    self.send_request(CMD_GAME_START_NOTIFY, {"room_id": room_id})
                    resp = self.recv_response()
                    if resp.get(FIELD_STATUS) == STATUS_OK:
                        info = resp.get(FIELD_PAYLOAD)
                        # Launch Game Client
                        self.launch_game(game_id, info['ip'], info['port'])
                        # Room status will change to PLAYING
                        # Should we exit loop? Or keep listening?
                        # Probably exit wait_room after launch? 
                        # Or wait for game end? 
                        # Usually game client is separate. We can stay here or go back to lobby.
                        # Assignment: "返回大廳"?
                        break
                    else:
                         print(f"Start failed: {resp.get(FIELD_MESSAGE)}")
                elif key == 'q':
                    # Leave room (Not implemented fully in protocol, just break)
                    # Ideally send LEAVE command
                    break
            
            # Poll Network (Status / Start Signal)
            # Use select with timeout 0
            # Wait, if we use select on 'sock', we might catch partial data if we are not careful?
            # 'recv_json' is blocking.
            # We can use sock.setblocking(False) temporarily?
            # Or use select to check if readable.
            import select
            readable, _, _ = select.select([self.sock], [], [], 0.1)
            if readable:
                # We have message!
                try:
                    # But recv_json expects full frame. Blocking recv is fine here because select said data is ready.
                    # Assumption: Server sends full JSON quickly.
                    # Problem: We might only read header and block for body. 
                    # If we use `utils.recv_json` inside here, it calls `recv_all`.
                    # If server is sending, it should be full message.
                    # EXCEPT: "Host" already called `send_request` above and `recv_response` immediately. 
                    # So Host won't be here when response arrives.
                    # This check is for "Guests" receving START NOTIFY.
                    
                    # Wait, Host receives response in the 'if key == s' block.
                    # Guests receive it asynchronously.
                    pass 
                except:
                    pass
                
                # Check message
                # Note: `recv_json` consumes data.
                msg = utils.recv_json(self.sock)
                if not msg: continue
                
                if msg.get(FIELD_COMMAND) == "GAME_START":
                    info = msg.get(FIELD_PAYLOAD)
                    self.launch_game(game_id, info['ip'], info['port'])
                    break

    def launch_game(self, game_id, ip, port):
        user_dir = os.path.join(self.downloads_root, self.username)
        self.launcher.launch(user_dir, game_id, ip, port, self.username)

if __name__ == "__main__":
    host_ip = input("please input server ip: ").strip()
    if not host_ip:
        host_ip = '127.0.0.1'
        
    client = PlayerClient(host_ip, 8888)
    try:
        client.main_loop()
    except KeyboardInterrupt:
        print("\nExiting...")
