import tkinter as tk
from tkinter import messagebox, Menu
from threading import Thread
from P_Server import P_Server
from P_Client import P_Client
import socket
import time
import threading


class RemoteControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AccessPoint - Desktop Remote Control")
        self.root.geometry("800x500")
        self.root.configure(bg="#d9ffcc")

        # Variables
        self.server = None
        self.server_code = None
        self.client = None
        self.entered_code = tk.StringVar()
        self.connection_status = tk.StringVar(value="No active connection")
        self.recent_connections = []  # To store recent connections

        # UI Components
        self.build_menu()
        self.build_left_panel()
        self.build_right_panel()

        # Start Server in Background
        self.server_thread = Thread(target=self.start_server, daemon=True)
        self.server_thread.start()

        # Start Client after Server Initialization
        self.client_thread = Thread(target=self.start_client, daemon=True)
        self.client_thread.start()

    def build_menu(self):
        menu_bar = Menu(self.root)
        self.root.config(menu=menu_bar)

        recent_menu = Menu(menu_bar, tearoff=0)
        recent_menu.add_command(label="Show Recent Connections", command=self.show_recent_connections)

        account_menu = Menu(menu_bar, tearoff=0)
        account_menu.add_command(label="Account Settings", command=self.account_settings)

        menu_bar.add_cascade(label="Recent Connections", menu=recent_menu)
        menu_bar.add_cascade(label="Account Settings", menu=account_menu)

    def build_left_panel(self):
        left_frame = tk.Frame(self.root, bg="#d9ffcc", bd=2, relief="solid")
        left_frame.place(x=50, y=50, width=350, height=400)

        tk.Label(left_frame, text="Your Connection Code", font=("Arial", 18, "bold"), bg="#d9ffcc").pack(pady=20)
        tk.Label(left_frame, text="Your Code Is:", font=("Arial", 14), bg="#d9ffcc").pack()

        self.code_label = tk.Label(left_frame, text="Loading...", font=("Arial", 20, "bold"), bg="white", width=10)
        self.code_label.pack(pady=20)

        icon = tk.Label(left_frame, text="💻", font=("Arial", 50), bg="#d9ffcc")
        icon.pack()

    def build_right_panel(self):
        right_frame = tk.Frame(self.root, bg="#d9ffcc", bd=2, relief="solid")
        right_frame.place(x=420, y=50, width=350, height=400)

        tk.Label(right_frame, text="Connection Information", font=("Arial", 18, "bold"), bg="#d9ffcc").pack(pady=20)

        tk.Label(right_frame, text="Enter code:", font=("Arial", 14), bg="#d9ffcc").pack()

        entry = tk.Entry(right_frame, textvariable=self.entered_code, font=("Arial", 14), bg="white", width=15)
        entry.pack(pady=10)

        connect_button = tk.Button(
            right_frame,
            text="Send connection request",
            font=("Arial", 12),
            bg="#a5d6a7",
            command=self.send_connection_request,
        )
        connect_button.pack(pady=20)

        status_label = tk.Label(
            right_frame, textvariable=self.connection_status, font=("Arial", 12), bg="#d9ffcc", wraplength=300
        )
        status_label.pack(pady=10)

    def start_server(self):
        """Start the server and set up the server code."""
        self.server = P_Server("0.0.0.0", 12345)  # Bind to all interfaces for external connections
        generated_code = self.server.generate_code(socket.gethostbyname(socket.gethostname()))
        self.server_code = generated_code
        self.server.start()

    def send_connection_request(self):
        entered_code = self.entered_code.get()

        if not entered_code.isdigit() or len(entered_code) != 4:
            messagebox.showerror("Error", "Invalid code! Enter a 4-digit code.")
            return

        if entered_code == self.server_code:
            messagebox.showerror("Connection Error", "You cannot connect to your own computer!")
            return

        def request_approval():
            self.client.send_request(entered_code)

            if self.client.approval_event.wait(timeout=30):
                if self.client.approval_result == "yes":
                    self.root.after(0, lambda: self.connection_status.set(f"Connected to: {entered_code}"))
                    self.recent_connections.append(entered_code)
                elif self.client.approval_result == "no":
                    self.root.after(0, lambda: self.connection_status.set("Connection request rejected."))
                else:
                    self.root.after(0, lambda: self.connection_status.set("Code not found or not connected."))
            else:
                self.root.after(0, lambda: self.connection_status.set("Connection request timed out."))

        Thread(target=request_approval, daemon=True).start()

    def show_recent_connections(self):
        connections = "\n".join(self.recent_connections) if self.recent_connections else "No recent connections."
        messagebox.showinfo("Recent Connections", connections)

    def account_settings(self):
        messagebox.showinfo("Account Settings", "Account settings feature coming soon!")

    def start_client(self):
        """Initialize and connect the client after the server is running."""
        time.sleep(1)  # Ensure server has started before client connects
        self.client = P_Client("127.0.0.1", 12345)  # Replace with actual server's external/public IP

        self.client.connect_to_server()

        def update_code():
            while not self.client.client_code:
                time.sleep(0.1)
            self.server_code = self.client.client_code
            self.root.after(0, self.update_code_label)

        threading.Thread(target=update_code, daemon=True).start()

    def update_code_label(self):
        self.code_label.config(text=self.server_code)


# Run the App
if __name__ == "__main__":
    root = tk.Tk()
    app = RemoteControlApp(root)
    root.mainloop()
