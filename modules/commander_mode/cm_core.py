from threading import Thread

class CM_Core():
    """Commander Mode core module for the Kill Tracker."""
    def __init__(self, logger, cm_gui, cm_api, update_queue):
        self.log = logger
        self.cm_gui = cm_gui
        self.cm_api = cm_api
        self.update_queue = update_queue
        self.connected_users = []
        self.alloc_users = []

    def allocate_selected_users(self) -> None:
        """Allocate selected Connected Users to Allocated Forces."""
        try:
            curr_alloc_users = [user["player"] for user in self.alloc_users]
            selected_indices = self.cm_gui.connected_users_listbox.curselection()
            for index in selected_indices:
                player_name = self.cm_gui.connected_users_listbox.get(index)
                # Find the full user info
                user_info = next((user for user in self.connected_users if user['player'] == player_name), None)
                if user_info and user_info["player"] not in curr_alloc_users:
                    # Add to allocated forces
                    self.alloc_users.append(user_info)
                    self.cm_gui.allocated_forces_insert(f"{user_info['player']} - Zone: {user_info['zone']}")
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
                    self.cm_gui.allocated_forces_insert(f"{conn_user['player']} - Zone: {conn_user['zone']}")
        except Exception as e:
            self.log.error(f"allocate_all_users(): Error: {e.__class__.__name__} - {e}")

    def update_allocated_forces(self) -> None:
        """Update the status of users in the allocated forces list."""
        try:
            for index in range(self.cm_gui.allocated_forces_listbox.size()):
                item_text = self.cm_gui.allocated_forces_listbox.get(index)
                # Extract the player's name
                player_name = item_text.split(" - ")[0]
                user = next((user for user in self.connected_users if user['player'] == player_name), None)
                # Remove allocated user
                del self.alloc_users[index]
                self.cm_gui.allocated_forces_listbox.delete(index)
                # Only re-add user if they are currently connected
                if user:
                    self.alloc_users.insert(index, user)
                    self.cm_gui.allocated_forces_listbox.insert(index, f"{user['player']} - Zone: {user['zone']}")
                    # Change text color of allocated users based on status
                    if user['status'] == "dead":
                        self.cm_gui.allocated_forces_listbox.itemconfig(index, {'fg': 'red'})
                    elif user['status'] == "alive":
                        self.cm_gui.allocated_forces_listbox.itemconfig(index, {'fg': 'green'})
        except Exception as e:
            self.log.error(f"update_allocated_forces(): Error: {e.__class__.__name__} - {e}")

    # Refresh User List Function
    def refresh_user_list(self, active_users) -> None:
        """Refresh the connected users list and update allocated forces based on status."""
        try:
            # Remove any dupes and sort alphabetically
            no_dupes = [dict(t) for t in {tuple(user.items()) for user in active_users}]
            self.connected_users = sorted(no_dupes, key=lambda user: user['player'])
            # Update Connected Users Listbox
            self.cm_gui.connected_users_delete()
            for user in self.connected_users:
                self.cm_gui.connected_users_insert(user['player'])
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
            if not self.update_queue.empty():
                active_commanders = self.update_queue.get()
                self.refresh_user_list(active_commanders)
            # Check again after a short delay
            self.cm_gui.commander_window.after(1000, self.check_for_cm_updates)  # Run every second
        except Exception as e:
            self.log.error(f"check_for_cm_updates(): Error: {e.__class__.__name__} - {e}")

    def clear_listboxes(self) -> None:
        """Cleanup listboxes when disconnected."""
        self.connected_users.clear()
        self.alloc_users.clear()
        self.cm_gui.connected_users_delete()
        self.cm_gui.allocated_forces_delete()

    def start_heartbeat_thread(self) -> None:
        """Start the heartbeat in a separate thread."""
        try:
            if self.heartbeat_daemon and not self.heartbeat_daemon.is_alive():
                self.log.info("Connecting to Commander...")
                self.heartbeat_daemon = Thread(target=self.cm_api.post_heartbeat, args=())
                self.heartbeat_daemon.daemon = True
                self.heartbeat_daemon.start()
            else:
                raise Exception("Already connected to commander!.")
        except Exception as e:
            self.log.error(f"start_heartbeat_thread(): {e.__class__.__name__} - {e}")

    def stop_heartbeat_thread(self) -> None:
        """Stop the heartbeat thread."""
        try:
            if self.heartbeat_daemon and self.heartbeat_daemon.is_alive():
                self.log.debug("Commander is shutting down...")
                self.heartbeat_status["active"] = False
                self.heartbeat_daemon.join(timeout=10)
                self.heartbeat_daemon = None
            else:
                raise Exception("Failed to disconnect from Commander.")
        except Exception as e:
            self.log.error(f"stop_heartbeat_thread(): {e.__class__.__name__} - {e}")