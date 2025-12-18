import sys
import socket
import threading

# Argument 1: Port
if len(sys.argv) < 2:
    print("Usage: python server.py <port>")
    sys.exit(1)

PORT = int(sys.argv[1])
HOST = '0.0.0.0'

clients = []
clients_lock = threading.Lock()

def broadcast(message, sender_conn):
    with clients_lock:
        for conn in clients:
            try:
                # Send to everyone (including sender, or not? usually yes for chat feel)
                # But Echo also sends back. Let's send to everyone.
                conn.sendall(message)
            except:
                pass

def handle_client(conn, addr):
    print(f"Game: New connection from {addr}")
    
    with clients_lock:
        clients.append(conn)
        
    try:
        conn.sendall(b"Welcome to the Global Chat Room!\n")
        
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                
                # Broadcast
                msg = f"User{addr[1]}: ".encode() + data
                broadcast(msg, conn)
            except ConnectionResetError:
                print(f"Game: Connection reset by {addr}")
                break
            except Exception as e:
                print(f"Game: Error reading from {addr}: {e}")
                break
    finally:
        with clients_lock:
            if conn in clients:
                clients.remove(conn)
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
