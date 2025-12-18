import socket
import sys
import json
import os
import io
import zipfile

# Adjust path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.protocol import *
import shared.utils as utils
try:
    from create_game_template import create_game_template
except ImportError:
    # Fallback if running from a different context
    pass

HOST = input("please input server ip: ")
PORT = 8888

class DeveloperClient:
    def __init__(self):
        self.sock = None
        self.token = None
        self.username = None

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((HOST, PORT))
            print(f"Connected to server at {HOST}:{PORT}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def send_request(self, command, payload):
        req = {FIELD_COMMAND: command, FIELD_PAYLOAD: payload}
        # Inject token if available
        if self.token:
            payload[FIELD_TOKEN] = self.token
            
        utils.send_json(self.sock, req)
        return utils.recv_json(self.sock)

    def main_loop(self):
        if not self.connect():
            return

        while True:
            if not self.token:
                self.auth_menu()
            else:
                self.dev_menu()

    def auth_menu(self):
        print("\n=== Developer Auth ===")
        print("1. Register")
        print("2. Login")
        print("3. Exit")
        choice = input("Select (1-3): ")

        if choice == '1':
            user = input("Username: ")
            pwd = input("Password: ")
            resp = self.send_request(CMD_DEV_REGISTER, {"username": user, "password": pwd})
            print(f"Result: {resp.get(FIELD_MESSAGE)}")
        elif choice == '2':
            user = input("Username: ")
            pwd = input("Password: ")
            resp = self.send_request(CMD_DEV_LOGIN, {"username": user, "password": pwd})
            if resp.get(FIELD_STATUS) == STATUS_OK:
                self.token = resp.get(FIELD_TOKEN)
                self.username = user
                # Setup local workspace
                self.workspace = os.path.join("developer_data", self.username)
                if not os.path.exists(self.workspace):
                    os.makedirs(self.workspace)
                print(f"Login successful. Welcome {user}!")
                print(f"Your workspace: {self.workspace}")
            else:
                print(f"Login failed: {resp.get(FIELD_MESSAGE)}")
        elif choice == '3':
            sys.exit(0)

    def dev_menu(self):
        print(f"\n=== Developer Menu ({self.username}) ===")
        print("0. Create New Game Projects")
        print("1. List Local Projects (Workspace)")
        print("2. List My Published Games (Server)")
        print("3. Upload New Game")
        print("4. Update Game") # reuse upload roughly
        print("5. Delete Game")
        print("6. Logout")
        choice = input("Select: ")

        if choice == '0':
            self.create_template()
        elif choice == '1':
            self.list_local_projects()
        elif choice == '2':
            self.list_games()
        elif choice == '3':
            self.upload_game()
        elif choice == '4':
            self.upload_game(is_update=True)
        elif choice == '5':
            self.delete_game()
        elif choice == '6':
            self.token = None
            self.username = None

    def list_local_projects(self):
        print(f"\n--- Local Projects ({self.workspace}) ---")
        if not os.path.exists(self.workspace):
            print("No simple workspace found.")
            return
            
        projects = [d for d in os.listdir(self.workspace) if os.path.isdir(os.path.join(self.workspace, d))]
        if not projects:
            print("No local projects found.")
            return
            
        for i, p in enumerate(projects):
            print(f"{i+1}. {p}")
        
    def list_games(self):
        resp = self.send_request(CMD_GAME_LIST_MY, {})
        if resp.get(FIELD_STATUS) == STATUS_OK:
            games = resp.get(FIELD_PAYLOAD, [])
            print("\n--- My Games ---")
            for g in games:
                print(f"[{g.get('game_id')}] {g.get('name')} v{g.get('version')} - {g.get('description')}")
        else:
            print(f"Error: {resp.get(FIELD_MESSAGE)}")

    def upload_game(self, is_update=False, target_path=None):
        if is_update:
             print("\n--- Update Game ---")
        else:
             print("\n--- Upload Game ---")
             
        if target_path:
            path = target_path
            print(f"Uploading from: {path}")
        else:
            # List local workspace projects
            if not os.path.exists(self.workspace):
                print(f"Workspace {self.workspace} does not exist.")
                return

            projects = [d for d in os.listdir(self.workspace) if os.path.isdir(os.path.join(self.workspace, d))]
            if not projects:
                print("No local projects found in workspace.")
                return

            print("\n--- Select Project to Upload ---")
            for i, p in enumerate(projects):
                print(f"{i+1}. {p}")
            
            choice = input("Select Number: ").strip()
            if not choice.isdigit():
                 print("Invalid selection.")
                 return
            
            idx = int(choice) - 1
            if idx < 0 or idx >= len(projects):
                print("Invalid selection.")
                return

            path = os.path.join(self.workspace, projects[idx])
        
        if not os.path.exists(path):
            print("Path does not exist!")
            return

        # Check config
        config_path = os.path.join(path, "config.json")
        if not os.path.exists(config_path):
            print("config.json missing in folder!")
            return

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Invalid config.json: {e}")
            return

        game_id = config.get("name").lower().replace(" ", "_")
        config["game_id"] = game_id

        # Version Update Prompt
        current_version = config.get("version", "1.0.0")
        if is_update:
            print(f"\n[UPDATE DETECTED] Current Version: v{current_version}")
            print("To publish an update, please enter the new version number.")
            new_ver = input(f"Enter new version (Press Enter to keep v{current_version}): ").strip()
            if new_ver:
                config["version"] = new_ver
                # Write back to file
                try:
                    with open(config_path, 'w') as f:
                        json.dump(config, f, indent=4)
                    print(f"Updated config.json to v{new_ver}")
                except Exception as e:
                    print(f"Failed to update config.json: {e}")

        # Zip the folder
        print("Zipping files...")
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(path):
                for file in files:
                    abs_file = os.path.join(root, file)
                    rel_file = os.path.relpath(abs_file, path)
                    zf.write(abs_file, rel_file)
        
        zip_data = mem_zip.getvalue()
        file_size = len(zip_data)
        
        # Protocol: Send Request -> Then Send Raw Bytes
        req = {
            FIELD_COMMAND: CMD_GAME_UPLOAD,
            FIELD_PAYLOAD: {
                FIELD_TOKEN: self.token,
                "game_meta": config,
                "file_size": file_size
            }
        }
        
        print(f"Uploading {file_size} bytes...")
        utils.send_json(self.sock, req)
        self.sock.sendall(zip_data)
        
        # Wait for response
        resp = utils.recv_json(self.sock)
        if resp:
            print(f"Upload Result: {resp.get(FIELD_MESSAGE)}")
        else:
            print("No response from server")

    def delete_game(self):
        gid = input("Enter Game ID to delete: ")
        resp = self.send_request(CMD_GAME_DELETE, {"game_id": gid})
        print(f"Result: {resp.get(FIELD_MESSAGE)}")

    def create_template(self):
        try:
            from create_game_template import create_game_template
            # distinct local workspace
            created_path = create_game_template(base_dir=self.workspace)
            if created_path:
                print("\nWould you like to UPLOAD this game to the server now?")
                print("(This makes it available for you to management and for players to download)")
                choice = input("Upload now? (Y/n): ").lower()
                if choice != 'n':
                    self.upload_game(target_path=created_path)
                    
        except ImportError:
            print("Template script not found. Please run 'create_game_template.py' manually.")
            
if __name__ == "__main__":
    client = DeveloperClient()
    try:
        client.main_loop()
    except KeyboardInterrupt:
        print("\nExiting...")
