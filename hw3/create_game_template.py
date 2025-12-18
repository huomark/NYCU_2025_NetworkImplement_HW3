import os
import json
import sys

def create_game_template(base_dir="games"):
    print("=== Create New Game Project ===")
    game_name = input("Enter Game Name (e.g. 'My Awesome Game'): ").strip()
    if not game_name:
        print("Game name cannot be empty.")
        return

    game_id = game_name.lower().replace(" ", "_")
    
    # Ensure base_dir exists
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
        
    target_dir = os.path.join(base_dir, game_id)
    
    if os.path.exists(target_dir):
        print(f"Directory {target_dir} already exists!")
        return

    os.makedirs(target_dir)
    print(f"Creating game in {target_dir}...")

    # 1. config.json
    config = {
        "name": game_name,
        "version": "1.0.0",
        "description": "Description of " + game_name,
        "type": "CLI",
        "min_players": 1,
        "max_players": 2,
        "entry_point": "server.py",
        "client_entry_point": "client.py"
    }
    
    with open(os.path.join(target_dir, "config.json"), 'w') as f:
        json.dump(config, f, indent=4)

    # 2. server.py template
    server_code = """import sys
import socket
import threading

# Argument 1: Port
if len(sys.argv) < 2:
    print("Usage: python server.py <port>")
    sys.exit(1)

PORT = int(sys.argv[1])
HOST = '0.0.0.0'

def handle_client(conn, addr):
    print(f"Game: New connection from {addr}")
    conn.sendall(b"Welcome to " + b"%s" + b"!\\n")
    while True:
        data = conn.recv(1024)
        if not data:
            break
        # Echo
        conn.sendall(b"Echo: " + data)
    conn.close()

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()
    print(f"Game Server listening on {PORT}")
    
    while True:
        conn, addr = s.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr))
        t.start()

if __name__ == "__main__":
    main()
""" % game_name.encode()

    with open(os.path.join(target_dir, "server.py"), 'w') as f:
        f.write(server_code)

    # 3. client.py template
    client_code = """import sys
import socket
import threading

# Usage: python client.py <ip> <port> <username>

if len(sys.argv) < 3:
    print("Usage: python client.py <ip> <port>")
    sys.exit(1)

HOST = sys.argv[1]
PORT = int(sys.argv[2])

def receive_loop(sock):
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                break
            print(data.decode(), end='')
        except:
            break

def main():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    print(f"Connected to Game Server at {HOST}:{PORT}")
    
    t = threading.Thread(target=receive_loop, args=(s,))
    t.daemon = True
    t.start()
    
    try:
        while True:
            msg = input()
            s.sendall(msg.encode() + b'\\n')
    except:
        pass
    finally:
        s.close()

if __name__ == "__main__":
    main()
"""
    with open(os.path.join(target_dir, "client.py"), 'w') as f:
        f.write(client_code)

    print(f"\n[SUCCESS] Game project created at: {target_dir}")
    print("-------------------------------------------------------")
    print("NEXT STEPS:")
    print(f"1. Open the folder '{target_dir}' to see the files.")
    print("2. 'config.json' : Game settings (name, version, etc.)")
    print("3. 'server.py'   : The logic that runs on the Game Server.")
    print("4. 'client.py'   : The logic that runs on the Player's terminal.")
    print("-------------------------------------------------------")
    
    return target_dir

if __name__ == "__main__":
    create_game_template()
