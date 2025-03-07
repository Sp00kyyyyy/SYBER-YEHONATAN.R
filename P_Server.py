import socket
import threading
import random
import json
import os
import time


class P_Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clients = {}  # {code: (conn, addr)}
        self.codes = self.load_codes()  # {ip: code}
        self.running = True

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Allow address reuse
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)  # Allow multiple clients
            self.server_socket.settimeout(1)  # Add timeout for accept
            print(f"Server started on {self.host}:{self.port}")
        except Exception as e:
            print(f"Error starting server: {e}")
            raise

    def load_codes(self):
        """Load existing codes from a file or initialize an empty dictionary."""
        try:
            if os.path.exists("client_codes.json"):
                with open("client_codes.json", "r") as file:
                    return json.load(file)
        except Exception as e:
            print(f"Error loading codes: {e}")
        return {}

    def save_codes(self):
        """Save the current codes to a file."""
        try:
            with open("client_codes.json", "w") as file:
                json.dump(self.codes, file)
        except Exception as e:
            print(f"Error saving codes: {e}")

    def generate_code(self, ip):
        """Generate or retrieve a permanent code for a unique IP."""
        if ip not in self.codes:
            # Generate a code that's not already in use
            while True:
                code = f"{random.randint(1000, 9999)}"
                if code not in self.codes.values():
                    break
            self.codes[ip] = code
            self.save_codes()
        return self.codes[ip]

    def handle_client(self, conn, addr):
        """Handle communication with a client."""
        ip = addr[0]
        code = self.generate_code(ip)
        self.clients[code] = (conn, addr)

        try:
            conn.send(f"CODE:{code}".encode())  # Send permanent code to client
            print(f"Client connected: {addr}, assigned code: {code}")
        except Exception as e:
            print(f"Error sending code to client {addr}: {e}")
            self.remove_client(code)
            return

        while code in self.clients and self.running:
            try:
                data = conn.recv(1024).decode()
                if not data:
                    break

                if ":" not in data:
                    print(f"Invalid data format from {addr}: {data}")
                    continue

                command, payload = data.split(":", 1)

                if command == "REQUEST":
                    target_code = payload
                    if target_code in self.clients and target_code != code:
                        target_conn, _ = self.clients[target_code]
                        try:
                            target_conn.send(f"APPROVE:{code}".encode())
                            print(f"Forwarded connection request from {code} to {target_code}")
                        except Exception as e:
                            print(f"Error forwarding request to {target_code}: {e}")
                            conn.send(f"ERROR: Target client is not responding.".encode())
                    elif target_code == code:
                        conn.send("ERROR: Cannot connect to yourself.".encode())
                    else:
                        conn.send("ERROR: Target code not found.".encode())

                elif command == "APPROVAL":
                    try:
                        requesting_code, decision = payload.split(",")
                        if requesting_code in self.clients:
                            requesting_conn, _ = self.clients[requesting_code]
                            requesting_conn.send(f"RESPONSE:{decision}".encode())
                            print(f"Forwarded approval response {decision} from {code} to {requesting_code}")
                        else:
                            print(f"Client {requesting_code} not found for approval")
                    except ValueError:
                        print(f"Invalid approval format from {addr}: {payload}")

            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error handling client {addr}: {e}")
                break

        self.remove_client(code)

    def remove_client(self, code):
        """Remove a client from the clients dictionary and close the connection."""
        if code in self.clients:
            conn, addr = self.clients[code]
            try:
                conn.close()
            except:
                pass
            del self.clients[code]
            print(f"Client {addr} disconnected")

    def start(self):
        """Start the server and accept incoming connections."""
        print("Server is running and waiting for connections...")
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                client_thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                client_thread.daemon = True
                client_thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error accepting connection: {e}")
                if not self.running:
                    break
                time.sleep(1)  # Wait before trying again

    def stop(self):
        """Stop the server and close all connections."""
        self.running = False

        # Close all client connections
        for code in list(self.clients.keys()):
            self.remove_client(code)

        # Close server socket
        try:
            self.server_socket.close()
        except:
            pass

        print("Server stopped")


if __name__ == "__main__":
    server = P_Server("0.0.0.0", 12345)  # Listen for external connections
    try:
        server.start()
    except KeyboardInterrupt:
        print("Server stopping...")
        server.stop()