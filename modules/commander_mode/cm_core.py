from threading import Thread
from time import sleep
# Inherit sub-modules
from modules.commander_mode.cm_api import CM_API_Client
from modules.commander_mode.cm_gui import CM_GUI

class CM_Core(CM_API_Client, CM_GUI):
    """Commander Mode core module for the Kill Tracker."""
    def __init__(self, gui_module, api_module, monitoring, heartbeat_status, rsi_handle, active_ship, update_queue):
        self.log = None
        self.gui = gui_module
        self.api_key = api_module.api_key
        self.api_fqdn = api_module.api_fqdn
        self.request_timeout = api_module.request_timeout
        self.monitoring = monitoring
        self.heartbeat_status = heartbeat_status
        self.rsi_handle = rsi_handle
        self.active_ship = active_ship
        self.update_queue = update_queue
        self.heartbeat_daemon = None
        self.cm_update_daemon = None
        self.commander_window = None
        self.connected_users = []
        self.connected_users_listbox = None
        self.alloc_users = []
        self.allocated_forces_listbox = None
        self.connect_commander_button = None
        self.join_timeout = 10
        self.heartbeat_interval = 5

        # Battle Tracking info
        self.is_commander = False
        self.mark_complete = False
        self.start_battle = False
        self.abort_command = False

    def allocate_selected_users(self) -> None:
        """Allocate selected Connected Users to Allocated Forces."""
        try:
            curr_alloc_users = [user["player"] for user in self.alloc_users]
            self.log.debug(f"allocate_selected_users(): curr_alloc_users: {curr_alloc_users}")
            selected_indices = self.connected_users_listbox.curselection()
            for index in selected_indices:
                player_name = self.connected_users_listbox.get(index)
                # Find the full user info
                user_info = next((user for user in self.connected_users if user['player'] == player_name), None)
                if user_info and user_info["player"] not in curr_alloc_users:
                    # Add to allocated forces
                    self.alloc_users.append(user_info)
                    self.log.debug(f"allocate_selected_users(): Inserting into allocated forces: {user_info}")
                    self.allocated_forces_insert(f"{user_info['player']} - Zone: {user_info['zone']}")
        except Exception as e:
            self.log.error(f"allocate_selected_users(): {e.__class__.__name__} - {e}")

    def allocate_all_users(self) -> None:
        """Allocate all Connected Users to Allocated Forces if not already in."""
        try:
            curr_alloc_users = [user["player"] for user in self.alloc_users]
            self.log.debug(f"allocate_all_users(): curr_alloc_users: {curr_alloc_users}")
            for conn_user in self.connected_users:
                if conn_user["player"] not in curr_alloc_users:
                    # Add to allocated forces
                    self.alloc_users.append(conn_user)
                    self.log.debug(f"allocate_all_users(): Inserting into allocated forces: {conn_user}")
                    self.allocated_forces_insert(f"{conn_user['player']} - Zone: {conn_user['zone']}")
        except Exception as e:
            self.log.error(f"allocate_all_users(): {e.__class__.__name__} - {e}")

    def take_command(self) -> None:
        """Start Tracking a battle"""
        try:
            self.is_commander = True
            self.post_heartbeat_event(None, None, None)
        except Exception as e:
            self.log.error(f"take_command(): {e.__class__.__name__} - {e}")

    def abort_command_func(self) -> None:
        """Set flag to abort command and discard remaining kill counts"""
        try:
            if self.is_commander:
                self.abort_command = True
                self.post_heartbeat_event(None, None, None)
                self.abort_command = False
                self.is_commander = False
        except Exception as e:
            self.log.error(f"abort_command(): {e.__class__.__name__} - {e}")

    def start_battle_func(self) -> None:
        """Set flag to abort command and discard remaining kill counts"""
        try:
            self.start_battle = True
            self.mark_complete = False
            self.post_heartbeat_event(None, None, None)
        except Exception as e:
            self.log.error(f"start_battle(): {e.__class__.__name__} - {e}")

    # TODO
    # def pass_command

    def mark_battle_complete_func(self) -> None:
        """Set flag to mark battle complete. Will take the name of the battle and post it with servitor."""
        try:
            self.start_battle = False
            self.mark_complete = True
            self.post_heartbeat_event(None, None, None)
        except Exception as e:
            self.log.error(f"mark_battle_complete(): {e.__class__.__name__} - {e}")

    # def reset_battle_counts(self) -> None:

    def update_allocated_forces(self) -> None:
        """Update the status of users in the allocated forces list."""
        try:
            for index in range(self.allocated_forces_listbox.size()):
                item_text = self.allocated_forces_listbox.get(index)
                # Extract the player's name
                player_name = item_text.split(" - ")[0]
                user = next((user for user in self.connected_users if user["player"] == player_name), None)
                # Remove allocated user
                del self.alloc_users[index]
                self.allocated_forces_listbox.delete(index)
                # Only re-add user if they are currently connected
                if user:
                    self.alloc_users.insert(index, user)
                    self.allocated_forces_listbox.insert(index, f"{user['player']} - Zone: {user['zone']}")
                    # Change text color of allocated users based on status
                    if user['status'] == "dead":
                        self.allocated_forces_listbox.itemconfig(index, {'fg': 'red'})
                    elif user['status'] == "alive":
                        self.allocated_forces_listbox.itemconfig(index, {'fg': '#04B431'})
        except Exception as e:
            self.log.error(f"update_allocated_forces(): {e.__class__.__name__} - {e}")

    # Refresh User List Function
    def refresh_user_list(self, active_users:dict) -> None:
        """Refresh the connected users list and update allocated forces based on status."""
        # Remove any dupes and sort alphabetically
        no_dupes = [dict(t) for t in {tuple(user.items()) for user in active_users}]
        self.connected_users = sorted(no_dupes, key=lambda user: user["player"])
        #self.log.debug(f"refresh_user_list(): initial connected users: {self.connected_users}")
        # Update Connected Users Listbox
        self.connected_users_delete()
        for user in self.connected_users:
            self.connected_users_insert(user["player"])
            #self.log.debug(f"refresh_user_list(): inserting into connected users: {user}")
        # Update Allocated Forces Listbox
        self.update_allocated_forces()

    def check_for_cm_updates(self) -> None:
        """
        Checks the update_queue for new commander data and refreshes the user list.
        This method should be called periodically from the Tkinter main loop.
        """
        while self.heartbeat_status["active"]:
            try:
                if not self.update_queue.empty():
                    active_commanders = self.update_queue.get()
                    #self.log.debug(f"check_for_cm_updates(): Received active commanders payload: {active_commanders}")
                    self.refresh_user_list(active_commanders)
                sleep(1)
            except Exception as e:
                self.log.error(f"check_for_cm_updates(): {e.__class__.__name__} - {e}")

    def start_heartbeat_threads(self) -> None:
        """Start the heartbeat threads."""
        try:
            if not self.heartbeat_daemon and not self.cm_update_daemon:
                self.log.info("Connecting to Commander...")
                self.heartbeat_daemon = Thread(target=self.post_heartbeat, daemon=True)
                self.heartbeat_daemon.start()
                self.log.debug(f"start_heartbeat_threads(): Started heartbeat thread.")
                self.cm_update_daemon = Thread(target=self.check_for_cm_updates, daemon=True)
                self.cm_update_daemon.start()
                self.log.debug(f"start_heartbeat_threads(): Started CM update thread.")
            else:
                raise Exception("Already connected to commander!")
        except Exception as e:
            self.log.error(f"Error(): {e}")

    def stop_heartbeat_threads(self) -> None:
        """Stop the heartbeat thread."""
        try:
            if (isinstance(self.heartbeat_daemon, Thread) and self.heartbeat_daemon.is_alive() and 
                isinstance(self.cm_update_daemon, Thread) and self.cm_update_daemon.is_alive()
            ):
                self.log.info("Commander is shutting down...")
                self.heartbeat_status["active"] = False
                self.clear_listboxes()
                self.heartbeat_daemon = None
                self.log.debug(f"stop_heartbeat_threads(): Stopped heartbeat thread.")
                self.cm_update_daemon = None
                self.log.debug(f"stop_heartbeat_threads(): Stopped CM update thread.")
                
            else:
                self.log.debug("stop_heartbeat_threads(): Commander Mode is not connected.")
        except Exception as e:
            self.log.error(f"stop_heartbeat_threads(): {e.__class__.__name__} - {e}")

    def clear_listboxes(self) -> None:
        """Cleanup listboxes when disconnected."""
        self.log.debug(f"clear_listboxes(): Data before clearing - connected_users: {self.connected_users}, alloc_users: {self.alloc_users}")
        self.connected_users.clear()
        self.alloc_users.clear()
        if self.commander_window:
            self.connected_users_delete()
            self.allocated_forces_delete()
        self.log.debug(f"clear_listboxes(): Data after clearing - connected_users: {self.connected_users}, alloc_users: {self.alloc_users}")
