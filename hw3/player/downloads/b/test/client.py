import sys
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
    import time
    for i in range(10):
        try:
            print(f"Connecting to {HOST}:{PORT} (Attempt {i+1}/10)...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            break
        except Exception as e:
            print(f"Connection failed: {e}")
            time.sleep(1)
    else:
        print("Could not connect after 10 attempts.")
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
    try:
        main()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
    finally:
        input("Press Enter to exit...")
