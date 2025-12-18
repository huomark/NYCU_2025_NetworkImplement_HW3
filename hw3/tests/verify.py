import sys
import os
import time
import json
import zipfile
import io

# Setup path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from developer.developer import DeveloperClient
from player.player import PlayerClient
from shared.protocol import *

def test_system():
    print("=== Starting Verification ===")
    
    # 1. Developer Flow
    dev = DeveloperClient()
    if not dev.connect():
        print("Server not running?")
        return
        
    print("[Dev] Registering...")
    resp = dev.send_request(CMD_DEV_REGISTER, {"username": "dev1", "password": "123"})
    print(f"Reg: {resp}")
    
    print("[Dev] Logging in...")
    resp = dev.send_request(CMD_DEV_LOGIN, {"username": "dev1", "password": "123"})
    if resp[FIELD_STATUS] != STATUS_OK:
        print("Dev Login Failed")
        return
    dev.token = resp[FIELD_TOKEN]
    
    # Upload
    print("[Dev] Uploading Game...")
    # Mocking upload logic from developer.py
    game_path = os.path.join("games", "template")
    with open(os.path.join(game_path, "config.json")) as f:
        config = json.load(f)
    config["game_id"] = "test_game" # force ID
    
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("config.json", json.dumps(config))
        zf.writestr("server.py", "print('Game Server Running')")
        zf.writestr("client.py", "print('Game Client Running')")
    zip_data = mem_zip.getvalue()
    
    req = {
        FIELD_COMMAND: CMD_GAME_UPLOAD,
        FIELD_PAYLOAD: {
            FIELD_TOKEN: dev.token,
            "game_meta": config,
            "file_size": len(zip_data)
        }
    }
    # Direct socket send
    import shared.utils as utils
    utils.send_json(dev.sock, req)
    dev.sock.sendall(zip_data)
    resp = utils.recv_json(dev.sock)
    print(f"Upload Resp: {resp}")
    dev.sock.close()
    
    # 2. Player Flow
    player = PlayerClient()
    if not player.connect(): return
    
    print("[Player] Registering...")
    player.send_request(CMD_PLAYER_REGISTER, {"username": "p1", "password": "123"})
    utils.recv_json(player.sock)
    
    print("[Player] Logging in...")
    player.send_request(CMD_PLAYER_LOGIN, {"username": "p1", "password": "123"})
    resp = utils.recv_json(player.sock)
    player.token = resp[FIELD_TOKEN]
    player.username = "p1"
    
    print("[Player] List Store...")
    player.send_request(CMD_STORE_LIST, {})
    resp = utils.recv_json(player.sock)
    print(f"Store: {len(resp[FIELD_PAYLOAD])} games found.")
    
    print("[Player] Downloading...")
    player.send_request(CMD_GAME_DOWNLOAD, {"game_id": "test_game"})
    resp = utils.recv_json(player.sock)
    size = resp.get("file_size")
    raw = utils.recv_all(player.sock, size)
    print(f"Downloaded {len(raw)} bytes.")
    
    # Cleanup downloads
    import shutil
    dpath = os.path.join("player", "downloads", "p1")
    if os.path.exists(dpath):
        shutil.rmtree(dpath)
        
    print("[Player] Creating Room...")
    # fake download existence
    os.makedirs(os.path.join(dpath, "test_game"), exist_ok=True)
    
    player.send_request(CMD_ROOM_CREATE, {"game_id": "test_game"})
    resp = utils.recv_json(player.sock)
    print(f"Room Create: {resp}")
    
    print("=== Verification Complete ===")

if __name__ == "__main__":
    test_system()
