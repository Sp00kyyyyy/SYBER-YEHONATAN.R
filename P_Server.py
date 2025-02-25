import socket
import threading
import random
import json
import os


class P_Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clients = {}  # {code: (conn, addr)}
        self.codes = self.load_codes()  # {ip: code}

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Server started on {self.host}:{self.port}")

    def load_codes(self):
        """Load existing codes from a file or initialize an empty dictionary."""
        if os.path.exists("client_codes.json"):
            with open("client_codes.json", "r") as file:
                return json.load(file)
        return {}

    def save_codes(self):
        """Save the current codes to a file."""
        with open("client_codes.json", "w") as file:
            json.dump(self.codes, file)

    def generate_code(self, ip):
        """Generate or retrieve a permanent code for a unique IP."""
        if ip not in self.codes:
            code = f"{random.randint(1000, 9999)}"
            self.codes[ip] = code
            self.save_codes()
        return self.codes[ip]

    def handle_client(self, conn, addr):
        """Handle communication with a client."""
        ip = addr[0]
        code = self.generate_code(ip)
        self.clients[code] = (conn, addr)
        conn.send(f"CODE:{code}".encode())  # Send permanent code to client
        print(f"Client connected: {addr}, assigned code: {code}")

        while True:
            try:
                data = conn.recv(1024).decode()
                if not data:
                    break

                command, payload = data.split(":", 1)

                if command == "REQUEST":
                    # Handle connection request
                    target_code = payload
                    if target_code in self.clients and target_code != code:
                        target_conn, _ = self.clients[target_code]
                        target_conn.send(f"APPROVE:{code}".encode())
                        print(f"Forwarded connection request from {code} to {target_code}")
                    elif target_code == code:
                        conn.send("ERROR: Cannot send a request to yourself.".encode())
                    else:
                        conn.send("ERROR: Target code not found or not connected.".encode())
                        print(f"Client {code} tried to connect to nonexistent or disconnected code {target_code}")

                elif command == "APPROVAL":
                    # Handle approval/rejection from target client
                    requesting_code, decision = payload.split(",")
                    if requesting_code in self.clients:
                        requesting_conn, _ = self.clients[requesting_code]
                        requesting_conn.send(f"RESPONSE:{decision}".encode())
                        print(f"Forwarded approval response {decision} from {code} to {requesting_code}")

            except Exception as e:
                print(f"Error handling client {addr}: {e}")
                break

        print(f"Client {addr} disconnected")
        del self.clients[code]
        conn.close()

    def start(self):
        """Start the server and accept incoming connections."""
        while True:
            conn, addr = self.server_socket.accept()
            threading.Thread(target=self.handle_client, args=(conn, addr)).start()


if __name__ == "__main__":
    # Use the LAN IP of the server machine
    server = P_Server(socket.gethostbyname(socket.gethostname()), 12345)
    server.start()
