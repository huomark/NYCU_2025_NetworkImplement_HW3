import socket
import selectors
import sys
import traceback

# Adjust path to handle module imports from root
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.db_manager import DBManager
from server.game_manager import GameManager
from server.request_handler import RequestHandler
import shared.utils as utils

HOST = '0.0.0.0'
PORT = 8888

sel = selectors.DefaultSelector()

def accept_wrapper(sock):
    conn, addr = sock.accept()
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)
    data = selectors.SimpleNamespace(addr=addr, inb=b'', outb=b'')
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)

def service_connection(key, mask, handler):
    sock = key.fileobj
    data = key.data
    
    if mask & selectors.EVENT_READ:
        # Using utils.recv_json which handles framing
        # But utils.recv_json is blocking (recv_all). 
        # For a true non-blocking selector server, we should buffer 'inb' and parse.
        # HOWEVER, adapting to `recv_json` which blocks -> we risk blocking the main loop.
        # Given HW scope, maybe threaded handling per request or just blocking read is acceptable if minimal.
        # Let's try to trust the client sends data quickly.
        # Better approach for this structure: Use a thread per client or blocking accept loop with threading.
        # But I partly committed to selectors in plan (implied concurrent).
        # Actually, let's switch to ThreadingMixIn or simple Threaded Server for simplicity with blocking Recv.
        # It's much easier to debug for students and handles the "recv_all" file upload blocking gracefully.
        pass

# Switch strategy: Threaded TCP Server
import socketserver

class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        print(f"Client {self.client_address} connected.")
        try:
            while True:
                # recv_json blocks until full message or disconnect
                request = utils.recv_json(self.request)
                if not request:
                    break
                
                # Handle
                response = self.server.app_handler.handle_request(request, self.request)
                
                # Check for raw data response (File Download)
                raw_data = response.pop("_raw_data", None)
                
                utils.send_json(self.request, response)
                
                if raw_data:
                    # Send raw bytes
                    self.request.sendall(raw_data)
                    
        except ConnectionResetError:
            pass
        except Exception as e:
            print(f"Error handling client {self.client_address}: {e}")
            traceback.print_exc()
        finally:
            print(f"Client {self.client_address} disconnected.")
            self.server.app_handler.handle_disconnect(self.request)

class GameStoreServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

def main():
    # Initialize Managers
    db_mgr = DBManager()
    game_mgr = GameManager()
    req_handler = RequestHandler(db_mgr, game_mgr)
    
    server = GameStoreServer((HOST, PORT), ThreadedTCPRequestHandler)
    server.app_handler = req_handler
    
    print(f"Server started on {HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Server shutting down...")
        server.shutdown()

if __name__ == "__main__":
    main()
