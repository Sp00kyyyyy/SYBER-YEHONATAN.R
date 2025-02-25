import socket
import threading
import tkinter as tk
from tkinter import messagebox


class P_Client:
    def __init__(self, server_host, server_port):
        self.server_host = server_host
        self.server_port = server_port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_code = None
        self.approval_event = threading.Event()
        self.approval_result = None

    def connect_to_server(self):
        """Connect to the server and start listening for messages."""
        self.server_socket.connect((self.server_host, self.server_port))
        threading.Thread(target=self.listen_to_server, daemon=True).start()

    def send_request(self, target_code):
        """Send a connection request to another client."""
        if target_code == self.client_code:
            print("ERROR: Cannot send a request to your own code.")
            return

        self.server_socket.send(f"REQUEST:{target_code}".encode())
        self.approval_event.clear()

        # Wait for approval for up to 5 minutes
        if self.approval_event.wait(timeout=300):
            if self.approval_result == "yes":
                print("Connection approved!")
            else:
                print("Connection rejected.")
        else:
            print("Connection request timed out.")

    def send_approval(self, requesting_code, decision):
        """Send approval or rejection to the server."""
        self.server_socket.send(f"APPROVAL:{requesting_code},{decision}".encode())

    def listen_to_server(self):
        """Listen for messages from the server."""
        while True:
            try:
                data = self.server_socket.recv(1024).decode()
                if data.startswith("CODE:"):
                    # Receive and store the permanent code
                    self.client_code = data.split(":")[1]
                    print(f"Your permanent code is: {self.client_code}")

                elif data.startswith("APPROVE:"):
                    # Receive connection approval request
                    requesting_code = data.split(":")[1]
                    if requesting_code != self.client_code:
                        decision = self.show_approval_dialog(requesting_code)
                        self.send_approval(requesting_code, "yes" if decision else "no")

                elif data.startswith("RESPONSE:"):
                    # Receive approval/rejection response
                    self.approval_result = data.split(":")[1]
                    self.approval_event.set()

                elif data.startswith("ERROR:"):
                    # Display error messages from the server
                    error_message = data.split(":", 1)[1]
                    print(f"Server Error: {error_message}")

            except Exception as e:
                print(f"Error receiving data: {e}")
                break

    def show_approval_dialog(self, requesting_code):
        """Show a dialog asking for approval of a connection request."""
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        decision = messagebox.askyesno(
            "Connection Request",
            f"Client {requesting_code} wants to connect. Approve?",
        )
        root.destroy()
        return decision


if __name__ == "__main__":
    # Replace with the LAN IP of the server
    client = P_Client("192.168.x.x", 12345)
    client.connect_to_server()
    while True:
        action = input("Enter 'r' to request a connection or 'q' to quit: ").lower()
        if action == "r":
            target = input("Enter the target code: ")
            client.send_request(target)
        elif action == "q":
            break
