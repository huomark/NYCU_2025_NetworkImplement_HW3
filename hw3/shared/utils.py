import json
import struct
import socket

def send_json(sock, data):
    """
    Sends a JSON object over the socket with a 4-byte length prefix.
    """
    json_bytes = json.dumps(data).encode('utf-8')
    # Prefix with 4-byte big-endian integer length
    msg = struct.pack('>I', len(json_bytes)) + json_bytes
    # print(f"DEBUG: Sending {len(msg)} bytes")
    sock.sendall(msg)

def recv_json(sock):
    """
    Receives a JSON object from the socket.
    Returns the parsed dictionary or None if disconnected.
    """
    # Read 4-byte length prefix
    raw_len = recv_all(sock, 4)
    if not raw_len:
        return None
    msg_len = struct.unpack('>I', raw_len)[0]
    # print(f"DEBUG: Expecting {msg_len} bytes")
    
    # Read payload
    payload = recv_all(sock, msg_len)

    if not payload:
        return None
    
    return json.loads(payload.decode('utf-8'))

def recv_all(sock, n):
    """
    Helper to receive exactly n bytes.
    """
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data
