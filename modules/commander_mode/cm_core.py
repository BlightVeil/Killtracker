from threading import Thread
from time import sleep
# Inherit sub-modules
from modules.commander_mode.cm_api import CM_API_Client
from modules.commander_mode.cm_gui import CM_GUI

class CM_Core(CM_API_Client, CM_GUI):
    """Commander Mode core module for the Kill Tracker."""
    def __init__(self, monitoring, api_module, heartbeat_status, rsi_handle, active_ship, update_queue):
        self.log = None
        self.monitoring = monitoring
        self.api_key = api_module.api_key
        self.api_fqdn = api_module.api_fqdn
        self.request_timeout = api_module.request_timeout
        self.heartbeat_status = heartbeat_status
        self.rsi_handle = rsi_handle
        self.active_ship = active_ship
        self.update_queue = update_queue
        self.connected_users = []
        self.connected_users_listbox = None
        self.alloc_users = []
        self.allocated_forces_listbox = None
        self.join_timeout = 10
        self.heartbeat_interval = 5
        self.heartbeat_daemon = None
        self.cm_update_daemon = None

    def allocate_selected_users(self) -> None:
        """Allocate selected Connected Users to Allocated Forces."""
        try:
            curr_alloc_users = [user["player"] for user in self.alloc_users]
            selected_indices = self.connected_users_listbox.curselection()
            for index in selected_indices:
                player_name = self.connected_users_listbox.get(index)
                # Find the full user info
                user_info = next((user for user in self.connected_users if user['player'] == player_name), None)
                if user_info and user_info["player"] not in curr_alloc_users:
                    # Add to allocated forces
                    self.alloc_users.append(user_info)
                    self.allocated_forces_insert(f"{user_info['player']} - Zone: {user_info['zone']}")
        except Exception as e:
            self.log.error(f"allocate_selected_users(): Error: {e.__class__.__name__} - {e}")

    def allocate_all_users(self) -> None:
        """Allocate all Connected Users to Allocated Forces if not already in."""
        try:
            curr_alloc_users = [user["player"] for user in self.alloc_users]
            for conn_user in self.connected_users:
                if conn_user["player"] not in curr_alloc_users:
                    # Add to allocated forces
                    self.alloc_users.append(conn_user)
                    self.allocated_forces_insert(f"{conn_user['player']} - Zone: {conn_user['zone']}")
        except Exception as e:
            self.log.error(f"allocate_all_users(): Error: {e.__class__.__name__} - {e}")

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
                        self.allocated_forces_listbox.itemconfig(index, {'fg': 'green'})
        except Exception as e:
            self.log.error(f"update_allocated_forces(): Error: {e.__class__.__name__} - {e}")

    # Refresh User List Function
    def refresh_user_list(self, active_users:dict) -> None:
        """Refresh the connected users list and update allocated forces based on status."""
        try:
            # Remove any dupes and sort alphabetically
            no_dupes = [dict(t) for t in {tuple(user.items()) for user in active_users}]
            self.connected_users = sorted(no_dupes, key=lambda user: user["player"])
            # Update Connected Users Listbox
            self.connected_users_delete()
            for user in self.connected_users:
                self.connected_users_insert(user["player"])
            # Update Allocated Forces Listbox
            self.update_allocated_forces()
        except Exception as e:
            self.log.error(f"refresh_user_list(): Error: {e.__class__.__name__} - {e}")

    def check_for_cm_updates(self) -> None:
        """
        Checks the update_queue for new commander data and refreshes the user list.
        This method should be called periodically from the Tkinter main loop.
        """
        try:
            while self.heartbeat_status["active"]:
                if not self.update_queue.empty():
                    active_commanders = self.update_queue.get()
                    self.refresh_user_list(active_commanders)
                sleep(1)
        except Exception as e:
            self.log.error(f"check_for_cm_updates(): Error: {e.__class__.__name__} - {e}")

    def start_heartbeat_threads(self) -> None:
        """Start the heartbeat threads."""
        try:
            if not self.heartbeat_daemon and not self.cm_update_daemon:
                self.log.info("Connecting to Commander...")
                self.heartbeat_daemon = Thread(target=self.post_heartbeat, daemon=True)
                self.heartbeat_daemon.start()
                self.cm_update_daemon = Thread(target=self.check_for_cm_updates, daemon=True)
                self.cm_update_daemon.start()
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
                self.heartbeat_daemon.join(self.join_timeout)
                self.heartbeat_daemon = None
                self.cm_update_daemon.join(self.join_timeout)
                self.cm_update_daemon = None
                self.clear_listboxes()
            else:
                raise Exception("Commander Mode is not connected.")
        except Exception as e:
            self.log.error(f"Error: {e}")

    def clear_listboxes(self) -> None:
        """Cleanup listboxes when disconnected."""
        self.connected_users.clear()
        self.alloc_users.clear()
        self.connected_users_delete()
        self.allocated_forces_delete()
