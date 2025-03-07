import tkinter as tk
from tkinter import messagebox, simpledialog, Menu
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
        self.recent_connections = []
        self.log_messages = []

        # UI Components
        self.build_menu()
        self.build_left_panel()
        self.build_right_panel()
        self.build_log_area()

        # Ask for Server IP Before Starting Client
        self.server_ip = simpledialog.askstring("Server IP", "Enter Server IP Address:", parent=self.root)
        if not self.server_ip:
            messagebox.showerror("Error", "Server IP is required!")
            self.root.destroy()
            return

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
        left_frame.place(x=50, y=50, width=350, height=300)

        tk.Label(left_frame, text="Your Connection Code", font=("Arial", 18, "bold"), bg="#d9ffcc").pack(pady=20)
        tk.Label(left_frame, text="Your Code Is:", font=("Arial", 14), bg="#d9ffcc").pack()

        self.code_label = tk.Label(left_frame, text="Loading...", font=("Arial", 20, "bold"), bg="white", width=10)
        self.code_label.pack(pady=20)

        icon = tk.Label(left_frame, text="💻", font=("Arial", 50), bg="#d9ffcc")
        icon.pack()

    def build_right_panel(self):
        right_frame = tk.Frame(self.root, bg="#d9ffcc", bd=2, relief="solid")
        right_frame.place(x=420, y=50, width=350, height=300)

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

    def build_log_area(self):
        # Add log area at the bottom
        log_frame = tk.Frame(self.root, bg="#e0e0e0", bd=2, relief="solid")
        log_frame.place(x=50, y=370, width=720, height=100)

        tk.Label(log_frame, text="Connection Log", font=("Arial", 10, "bold"), bg="#e0e0e0").pack(anchor="w", padx=5)

        # Create a scrollable text area for logs
        self.log_text = tk.Text(log_frame, height=4, width=80, font=("Arial", 9))
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Disable text editing
        self.log_text.config(state=tk.DISABLED)

    def log_message(self, message):
        """Add a message to the log area in the UI"""
        self.log_messages.append(message)
        # Use after method to update UI from any thread
        self.root.after(0, self._update_log_display)

    def _update_log_display(self):
        """Update the log text area with all messages"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        for msg in self.log_messages[-10:]:  # Show last 10 messages
            self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.config(state=tk.DISABLED)
        self.log_text.see(tk.END)  # Scroll to the end

    def start_server(self):
        """Start the server and set up the server code."""
        try:
            self.server = P_Server("0.0.0.0", 12345)
            local_ip = socket.gethostbyname(socket.gethostname())
            generated_code = self.server.generate_code(local_ip)
            self.server_code = generated_code
            self.log_message(f"Server started on {local_ip}:12345")
            self.log_message(f"Your connection code: {generated_code}")

            # Override the P_Server's print functionality
            original_print = print

            def custom_print(*args, **kwargs):
                message = " ".join(map(str, args))
                self.log_message(message)
                original_print(*args, **kwargs)

            import builtins
            builtins.print = custom_print

            self.server.start()
        except Exception as e:
            self.log_message(f"Server error: {str(e)}")
            messagebox.showerror("Server Error", f"Could not start server: {str(e)}")

    def send_connection_request(self):
        entered_code = self.entered_code.get()

        if not entered_code.isdigit() or len(entered_code) != 4:
            messagebox.showerror("Error", "Invalid code! Enter a 4-digit code.")
            return

        if entered_code == self.server_code:
            messagebox.showerror("Connection Error", "You cannot connect to your own computer!")
            return

        self.connection_status.set("Sending request...")
        self.log_message(f"Sending connection request to {entered_code}")

        def request_approval():
            try:
                self.client.send_request(entered_code)
                self.root.after(0, lambda: self.connection_status.set("Waiting for response..."))
                self.log_message(f"Waiting for approval from {entered_code}")

                if self.client.approval_event.wait(timeout=60):
                    if self.client.approval_result == "yes":
                        self.root.after(0, lambda: self.connection_status.set(f"Connected to: {entered_code}"))
                        self.log_message(f"Connection approved by {entered_code}")
                        self.recent_connections.append(entered_code)

                        # Here you would start the actual screen sharing/remote control
                        self.start_remote_control(entered_code)

                    elif self.client.approval_result == "no":
                        self.root.after(0, lambda: self.connection_status.set("Connection request rejected."))
                        self.log_message(f"Connection rejected by {entered_code}")
                    else:
                        self.root.after(0, lambda: self.connection_status.set("Code not found or not connected."))
                        self.log_message(f"Error: Code not found or not connected")
                else:
                    self.root.after(0, lambda: self.connection_status.set("Connection request timed out."))
                    self.log_message("Connection request timed out")
            except Exception as e:
                self.root.after(0, lambda: self.connection_status.set(f"Error: {str(e)}"))
                self.log_message(f"Connection error: {str(e)}")

        Thread(target=request_approval, daemon=True).start()

    def start_remote_control(self, target_code):
        """Start the remote control functionality after connection is established"""
        # This is where you would implement the actual screen sharing and remote control
        self.log_message(f"Starting remote control session with {target_code}")
        # For now, just a placeholder
        messagebox.showinfo("Remote Control", f"Remote control session with {target_code} would start here.")

    def show_recent_connections(self):
        connections = "\n".join(self.recent_connections) if self.recent_connections else "No recent connections."
        messagebox.showinfo("Recent Connections", connections)

    def account_settings(self):
        messagebox.showinfo("Account Settings", "Account settings feature coming soon!")

    def start_client(self):
        """Initialize and connect the client after the server is running."""
        try:
            time.sleep(1)  # Ensure server has started before client connects
            self.client = P_Client(self.server_ip, 12345)
            self.log_message(f"Connecting to server at {self.server_ip}:12345")

            # Override the P_Client's print functionality
            original_print = print

            def custom_print(*args, **kwargs):
                message = " ".join(map(str, args))
                self.log_message(message)
                original_print(*args, **kwargs)

            import builtins
            builtins.print = custom_print

            self.client.connect_to_server()
            self.log_message("Connected to server successfully")

            def update_code():
                timeout = 10  # seconds
                start_time = time.time()
                while not self.client.client_code:
                    if time.time() - start_time > timeout:
                        self.log_message("Timeout waiting for client code")
                        break
                    time.sleep(0.1)

                if self.client.client_code:
                    self.server_code = self.client.client_code
                    self.root.after(0, self.update_code_label)
                    self.log_message(f"Your code is: {self.client.client_code}")

            threading.Thread(target=update_code, daemon=True).start()
        except Exception as e:
            self.log_message(f"Client error: {str(e)}")
            messagebox.showerror("Client Error", f"Could not connect to server: {str(e)}")

    def update_code_label(self):
        """Update the label with the server-assigned code."""
        self.code_label.config(text=self.server_code)


# Run the App
if __name__ == "__main__":
    root = tk.Tk()
    app = RemoteControlApp(root)
    root.mainloop()