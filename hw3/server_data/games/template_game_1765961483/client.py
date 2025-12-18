import sys
import socket
import threading

# Usage: python client.py <ip> <port> <username> (optional)

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
            print(data.decode(), end='') # assume text
        except:
            break

def main():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
    except Exception as e:
        print(f"Failed to connect to game server: {e}")
        return

    print(f"Connected to Game Server at {HOST}:{PORT}")
    
    t = threading.Thread(target=receive_loop, args=(s,))
    t.daemon = True
    t.start()
    
    try:
        while True:
            msg = input()
            s.sendall(msg.encode() + b'\n')
    except:
        pass
    finally:
        s.close()

if __name__ == "__main__":
    main()
