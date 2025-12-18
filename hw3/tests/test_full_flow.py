import sys
import os
import time
import json
import zipfile
import io
import socket
import threading

# Setup path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from developer.developer import DeveloperClient
from player.player import PlayerClient
from shared.protocol import *
import shared.utils as utils

def check_game_server(ip, port):
    time.sleep(1) # wait for startup
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        data = s.recv(1024)
        print(f"[Check] Connected to Game Server. Received: {data}")
        s.close()
        return True
    except Exception as e:
        print(f"[Check] Failed to connect to Game Server: {e}")
        return False

def test_full_flow():
    print("=== Starting Full Flow Test ===")
    
    # 0. Setup: Real game template
    game_path = os.path.join("games", "template")
    if not os.path.exists(game_path):
        print("Template invalid")
        return

    # 1. Developer: Upload Game
    dev = DeveloperClient()
    if not dev.connect(): return
    dev_user = "test_dev_" + str(int(time.time()))
    dev.send_request(CMD_DEV_REGISTER, {"username": dev_user, "password": "123"})
    resp = dev.send_request(CMD_DEV_LOGIN, {"username": dev_user, "password": "123"})
    dev.token = resp[FIELD_TOKEN]
    dev.username = dev_user
    
    # Upload
    print(f"[Dev] Uploading Real Template...")
    # Load config
    with open(os.path.join(game_path, "config.json")) as f:
        config = json.load(f)
    game_id = config["name"].replace(" ", "_").lower() + "_" + str(int(time.time()))
    config["game_id"] = game_id # Ensure ID
    
    # Zip real files
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(game_path):
            for file in files:
                abs_file = os.path.join(root, file)
                rel_file = os.path.relpath(abs_file, game_path)
                zf.write(abs_file, rel_file)
    zip_data = mem_zip.getvalue()
    
    req = {
        FIELD_COMMAND: CMD_GAME_UPLOAD,
        FIELD_PAYLOAD: {
            FIELD_TOKEN: dev.token,
            "game_meta": config,
            "file_size": len(zip_data)
        }
    }
    utils.send_json(dev.sock, req)
    dev.sock.sendall(zip_data)
    resp = utils.recv_json(dev.sock)
    print(f"[Dev] Upload Resp: {resp}")
    if resp[FIELD_STATUS] != STATUS_OK: return

    # 1.5 Developer: Update Game (D2)
    print(f"[Dev] Updating Game Version...")
    config["version"] = "1.0.1"
    req_update = {
         FIELD_COMMAND: CMD_GAME_UPLOAD, # Use Upload for Update
         FIELD_PAYLOAD: {
             FIELD_TOKEN: dev.token,
             "game_meta": config,
             "file_size": len(zip_data)
         }
    }
    utils.send_json(dev.sock, req_update)
    dev.sock.sendall(zip_data)
    resp = utils.recv_json(dev.sock)
    print(f"[Dev] Update Resp: {resp}")

    # 2. Player: Download (P2)
    p1 = PlayerClient()
    p1.connect()
    p1_user = "p1_" + str(int(time.time()))
    p1.send_request(CMD_PLAYER_REGISTER, {"username": p1_user, "password": "123"})
    print(f"[Player] Register request sent. Response: {p1.recv_response()}")
    
    p1.send_request(CMD_PLAYER_LOGIN, {"username": p1_user, "password": "123"})
    resp = p1.recv_response() 
    if resp[FIELD_STATUS] != STATUS_OK:
        print(f"Login Failed: {resp}")
        return
    p1.token = resp[FIELD_TOKEN]
    p1.username = p1_user
    
    print("[Player] Downloading Game...")
    p1.send_request(CMD_GAME_DOWNLOAD, {"game_id": game_id})
    resp = p1.recv_response()
    if resp[FIELD_STATUS] == STATUS_OK:
        raw = utils.recv_all(p1.sock, resp["file_size"])
        # Save
        dpath = os.path.join("player", "downloads", p1_user, game_id)
        if os.path.exists(dpath): shutil.rmtree(dpath)
        os.makedirs(dpath)
        with open(os.path.join(dpath, "pkg.zip"), 'wb') as f: f.write(raw)
        with zipfile.ZipFile(os.path.join(dpath, "pkg.zip"), 'r') as zf:
            zf.extractall(dpath)
        print("[Player] Downloaded and Extracted.")
    else:
        print(f"Download Failed: {resp}")
        return

    # 3. Player: Create Room & Start (P3)
    print("[Player] Creating Room...")
    p1.send_request(CMD_ROOM_CREATE, {"game_id": game_id})
    resp = p1.recv_response()
    room_id = resp[FIELD_PAYLOAD]["room_id"]
    print(f"Room {room_id} Created.")
    
    print("[Player] Starting Game...")
    p1.send_request(CMD_GAME_START_NOTIFY, {"room_id": room_id})
    resp = p1.recv_response() # Should get Port
    print(f"[Player] Start Resp: {resp}")
    
    if resp[FIELD_STATUS] == STATUS_OK:
        port = resp[FIELD_PAYLOAD]["port"]
        ip = resp[FIELD_PAYLOAD]["ip"]
        if check_game_server(ip, port):
            print("SUCCESS: Game Server is reachable!")
        else:
            print("FAILURE: Game Server unreachable.")
    else:
        print("Start Failed")

    print("=== Test Complete ===")
    p1.sock.close()
    dev.sock.close()

if __name__ == "__main__":
    test_full_flow()
