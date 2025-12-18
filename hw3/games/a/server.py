import sys
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
    conn.sendall(b"Welcome to " + b"b'a'" + b"!\n")
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
