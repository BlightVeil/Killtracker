import tkinter as tk

class CM_GUI():
    """Commander Mode API module for the Kill Tracker."""
    def __init__(self, logger, api_client_module):
        self.log = logger
        self.api = api_client_module
        self.commander_window = tk.Toplevel()
        self.connected_users_listbox = None
        self.allocated_forces_listbox = None

    def connected_users_insert(self, player_data):
        """Insert into connected users GUI element"""
        self.connected_users_listbox.insert(tk.END, player_data)

    def connected_users_delete(self):
        """Delete from connected users GUI element"""
        self.connected_users_listbox.delete(0, tk.END)

    def allocated_forces_insert(self, player_data):
        """Insert into allocated forces GUI element"""
        self.allocated_forces_listbox.insert(tk.END, player_data)

    def allocated_forces_delete(self):
        """Delete from allocated forces GUI element"""
        self.allocated_forces_listbox.delete(0, tk.END)

    def config_search_bar(self, widget, placeholder_text):
        """Handle search bar for filtering connected users."""
        def remove_placeholder(event):
            placeholder_text = getattr(event.widget, "placeholder", "")
            if placeholder_text and event.widget.get() == placeholder_text:
                event.widget.delete(0, tk.END)
        
        def add_placeholder(event):
            placeholder_text = getattr(event.widget, "placeholder", "")
            if placeholder_text and event.widget.get() == "":
                event.widget.insert(0, placeholder_text)

        widget.placeholder = placeholder_text
        if widget.get() == "":
            widget.insert(tk.END, placeholder_text)
        # Set up bindings to handle placeholder text
        widget.bind("<FocusIn>", remove_placeholder)
        widget.bind("<FocusOut>", add_placeholder)

    def open_commander_mode(self):
        """
        Opens a new window for Commander Mode, displaying connected users and allocated forces.
        Includes functionality for moving users to the allocated forces list and handling status changes.
        """
        self.commander_window.title("Commander Mode")
        self.commander_window.minsize(width=1280, height=720)
        self.commander_window.configure(bg="#484759")
        self.commander_window.protocol("WM_DELETE_WINDOW", self.destroy_window)

        # Search bar for filtering connected users
        search_var = tk.StringVar()
        search_bar = tk.Entry(self.commander_window, textvariable=search_var, font=("Consolas", 12), width=30)
        self.config_search_bar(search_bar, "Search Connected Users...")
        search_bar.pack(pady=(10, 0))

        # Connected Users Listbox
        connected_users_frame = tk.Frame(
            self.commander_window, bg="#484759"
        )
        connected_users_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 5), pady=(5, 10))

        connected_users_label = tk.Label(
            connected_users_frame, text="Connected Users", font=("Times New Roman", 12), fg="#ffffff", bg="#484759"
        )
        connected_users_label.pack()

        self.connected_users_listbox = tk.Listbox(
            connected_users_frame, selectmode=tk.MULTIPLE, width=40, height=20, font=("Consolas", 12), bg="#282a36", fg="#f8f8f2"
        )
        self.connected_users_listbox.pack(fill=tk.BOTH, expand=True)

        # Allocated Forces Listbox
        allocated_forces_frame = tk.Frame(
            self.commander_window, bg="#484759"
        )
        allocated_forces_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 10), pady=(5, 10))

        allocated_forces_label = tk.Label(
            allocated_forces_frame, text="Allocated Forces", font=("Times New Roman", 12), fg="#ffffff", bg="#484759"
        )
        allocated_forces_label.pack()

        self.allocated_forces_listbox = tk.Listbox(
            allocated_forces_frame, width=40, height=20, font=("Consolas", 12), bg="#282a36", fg="#ff0000"
        )
        self.allocated_forces_listbox.pack(fill=tk.BOTH, expand=True)

        # Add User To Fleet Button
        add_user_to_fleet_button = tk.Button(
            self.commander_window, text="Add User to Fleet", font=("Times New Roman", 12), command=lambda: self.cm_core.allocate_selected_users(), bg="#000000", fg="#ffffff"
        )
        add_user_to_fleet_button.pack(pady=(10, 10))

        # Add All To Fleet Button
        add_all_to_fleet_button = tk.Button(
            self.commander_window, text="Add All Users to Fleet", font=("Times New Roman", 12), command=lambda: self.cm_core.allocate_all_users(), bg="#000000", fg="#ffffff"
        )
        add_all_to_fleet_button.pack(pady=(10, 10))
        
        start_heartbeat_button = tk.Button(
            self.commander_window, text="Connect to Commander", font=("Times New Roman", 12), command=lambda: self.cm_core.start_heartbeat_thread(), bg="#000000", fg="#ffffff"
        )
        start_heartbeat_button.pack(pady=(10, 10))

        # Close Button
        dc_button = tk.Button(
            self.commander_window, text="Disconnect", font=("Times New Roman", 12), command=lambda:[self.cm_core.stop_heartbeat_thread(), self.cm_core.clear_listboxes()], bg="#000000", fg="#ffffff"
        )
        dc_button.pack(pady=(10, 10))

        # Search Functionality
        def search_users(*args):
            search_query = search_var.get().lower()
            self.connected_users_listbox.delete(0, tk.END)
            if self.cm_core.connected_users:
                for user in self.cm_core.connected_users:
                    if search_query in user['player'].lower():
                        self.connected_users_listbox.insert(tk.END, user['player'])

        search_var.trace("w", search_users)
    
    def destroy_window(self):
        """Stop heartbeat if window is closed"""
        self.commander_window.destroy()
        self.cm_core.stop_heartbeat_thread()
