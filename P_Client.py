import socket
import threading
import tkinter as tk
from tkinter import messagebox


class P_Client:
    def __init__(self, server_host, server_port):
        self.server_host = server_host
        self.server_port = server_port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.settimeout(10)  # Add timeout for connection attempts
        self.client_code = None
        self.approval_event = threading.Event()
        self.approval_result = None
        self.connected = False

    def connect_to_server(self):
        """Connect to the server and start listening for messages."""
        try:
            self.server_socket.connect((self.server_host, self.server_port))
            self.connected = True
            threading.Thread(target=self.listen_to_server, daemon=True).start()
            return True
        except socket.error as e:
            print(f"Connection failed: {e}")
            return False

    def send_request(self, target_code):
        """Send a connection request to another client."""
        if not self.connected:
            print("Not connected to server")
            return False

        if target_code == self.client_code:
            print("ERROR: Cannot send a request to your own code.")
            return False

        try:
            self.server_socket.send(f"REQUEST:{target_code}".encode())
            self.approval_event.clear()
            return True
        except socket.error as e:
            print(f"Error sending request: {e}")
            return False

    def send_approval(self, requesting_code, decision):
        """Send approval or rejection to the server."""
        if not self.connected:
            print("Not connected to server")
            return False

        try:
            self.server_socket.send(f"APPROVAL:{requesting_code},{decision}".encode())
            return True
        except socket.error as e:
            print(f"Error sending approval: {e}")
            return False

    def listen_to_server(self):
        """Listen for messages from the server."""
        while self.connected:
            try:
                data = self.server_socket.recv(1024).decode()
                if not data:
                    print("Server connection closed")
                    self.connected = False
                    break

                if data.startswith("CODE:"):
                    self.client_code = data.split(":")[1]
                    print(f"Your permanent code is: {self.client_code}")

                elif data.startswith("APPROVE:"):
                    requesting_code = data.split(":")[1]
                    decision = self.show_approval_dialog(requesting_code)
                    self.send_approval(requesting_code, "yes" if decision else "no")

                elif data.startswith("RESPONSE:"):
                    self.approval_result = data.split(":")[1]
                    self.approval_event.set()

                elif data.startswith("ERROR:"):
                    error_message = data.split(':', 1)[1]
                    print(f"Server Error: {error_message}")
                    # If this is a response to a connection request, set the approval event
                    if "not found" in error_message or "yourself" in error_message:
                        self.approval_result = "error"
                        self.approval_event.set()

            except socket.timeout:
                print("Socket timeout while listening")
                continue
            except ConnectionResetError:
                print("Connection was reset by the server")
                self.connected = False
                break
            except ConnectionAbortedError:
                print("Connection was aborted")
                self.connected = False
                break
            except Exception as e:
                print(f"Error receiving data: {e}")
                self.connected = False
                break

        print("Disconnected from server")

    def show_approval_dialog(self, requesting_code):
        """Show a dialog asking for approval of a connection request."""
        # Create a new root window for the dialog
        result = [False]  # Use a list to store the result

        def show_dialog():
            root = tk.Tk()
            root.withdraw()
            decision = messagebox.askyesno("Connection Request",
                                           f"Client {requesting_code} wants to connect. Approve?")
            result[0] = decision
            root.destroy()

        # Run the dialog in the main thread
        if threading.current_thread() is threading.main_thread():
            show_dialog()
        else:
            # Schedule the dialog to run on the main thread
            tk.CallWrapper(show_dialog)

        return result[0]

    def disconnect(self):
        """Disconnect from the server."""
        if self.connected:
            try:
                self.server_socket.close()
            except:
                pass
            self.connected = False