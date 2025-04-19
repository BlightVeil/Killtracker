
#CommanderMode
def open_commander_mode(logger):
    """
    Opens a new window for Commander Mode, displaying connected users and allocated forces.
    Includes functionality for moving users to the allocated forces list and handling status changes.
    """
    commander_window = tk.Toplevel()
    commander_window.title("Commander Mode")
    commander_window.minsize(width=1280, height=720)
    commander_window.configure(bg="#484759")

    def config_search_bar(widget, placeholder_text):
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

    # Search bar for filtering connected users
    search_var = tk.StringVar()
    search_bar = tk.Entry(commander_window, textvariable=search_var, font=("Consolas", 12), width=30)
    config_search_bar(search_bar, "Search Connected Users...")
    search_bar.pack(pady=(10, 0))

    # Connected Users Listbox
    connected_users_frame = tk.Frame(commander_window, bg="#484759")
    connected_users_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 5), pady=(5, 10))

    connected_users_label = tk.Label(
        connected_users_frame, text="Connected Users", font=("Times New Roman", 12), fg="#ffffff", bg="#484759"
    )
    connected_users_label.pack()

    connected_users_listbox = tk.Listbox(
        connected_users_frame, 
        selectmode=tk.MULTIPLE,
        width=40,
        height=20,
        bg="#282a36",
        fg="#f8f8f2",
        font=("Consolas", 12)
    )
    connected_users_listbox.pack(fill=tk.BOTH, expand=True)

    # Allocated Forces Listbox
    allocated_forces_frame = tk.Frame(commander_window, bg="#484759")
    allocated_forces_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 10), pady=(5, 10))

    allocated_forces_label = tk.Label(
        allocated_forces_frame, text="Allocated Forces", font=("Times New Roman", 12), fg="#ffffff", bg="#484759"
    )
    allocated_forces_label.pack()

    allocated_forces_listbox = tk.Listbox(
        allocated_forces_frame, 
        width=40,
        height=20,
        bg="#282a36",
        fg="#ff0000",  # Default to red (dead)
        font=("Consolas", 12)
    )
    allocated_forces_listbox.pack(fill=tk.BOTH, expand=True)

    # Add User To Fleet Button
    add_user_to_fleet_button = tk.Button(
        commander_window,
        text="Add User to Fleet",
        font=("Times New Roman", 12),
        command=lambda: allocate_selected_users(),
        bg="#000000",
        fg="#ffffff",
    )
    add_user_to_fleet_button.pack(pady=(10, 10))

    # Add All To Fleet Button
    add_all_to_fleet_button = tk.Button(
        commander_window,
        text="Add All Users to Fleet",
        font=("Times New Roman", 12),
        command=lambda: allocate_all_users(),
        bg="#000000",
        fg="#ffffff",
    )
    add_all_to_fleet_button.pack(pady=(10, 10))
    
    start_heartbeat_button = tk.Button(
        commander_window,
        text="Connect to Commander",
        font=("Times New Roman", 12),
        command=lambda: start_heartbeat_thread(logger),  # Pass logger here
        bg="#000000",
        fg="#ffffff",
    )
    start_heartbeat_button.pack(pady=(10, 10))

    # Close Button
    dc_button = tk.Button(
        commander_window,
        text="Disconnect",
        font=("Times New Roman", 12),
        command=lambda:[stop_heartbeat_thread(logger), clear_listboxes()],
        bg="#000000",
        fg="#ffffff",
    )
    dc_button.pack(pady=(10, 10))

    # Search Functionality
    def search_users(*args):
        search_query = search_var.get().lower()
        connected_users_listbox.delete(0, tk.END)
        if logger.connected_users:
            for user in logger.connected_users:
                if search_query in user['player'].lower():
                    connected_users_listbox.insert(tk.END, user['player'])

    search_var.trace("w", search_users)

    def allocate_selected_users() -> None:
        """Allocate selected Connected Users to Allocated Forces."""
        try:
            curr_alloc_users = [user["player"] for user in logger.alloc_users]
            selected_indices = connected_users_listbox.curselection()
            for index in selected_indices:
                player_name = connected_users_listbox.get(index)
                # Find the full user info
                user_info = next((user for user in logger.connected_users if user['player'] == player_name), None)
                if user_info and user_info["player"] not in curr_alloc_users:
                    # Add to allocated forces
                    logger.alloc_users.append(user_info)
                    allocated_forces_listbox.insert(tk.END, f"{user_info['player']} - Zone: {user_info['zone']}")
        except Exception as e:
            logger.log(f"⚠️ ERROR allocate_selected_users(): {e.__class__.__name__} - {e}")

    def allocate_all_users() -> None:
        """Allocate all Connected Users to Allocated Forces if not already in."""
        try:
            curr_alloc_users = [user["player"] for user in logger.alloc_users]
            for conn_user in logger.connected_users:
                if conn_user["player"] not in curr_alloc_users:
                    # Add to allocated forces
                    logger.alloc_users.append(conn_user)
                    allocated_forces_listbox.insert(tk.END, f"{conn_user['player']} - Zone: {conn_user['zone']}")
        except Exception as e:
            logger.log(f"⚠️ ERROR allocate_all_users(): {e.__class__.__name__} - {e}")

    def allocate_selected_users() -> None:
        """Allocate selected Connected Users to Allocated Forces."""
        try:
            curr_alloc_users = [user["player"] for user in logger.alloc_users]
            selected_indices = connected_users_listbox.curselection()
            for index in selected_indices:
                player_name = connected_users_listbox.get(index)
                # Find the full user info
                user_info = next((user for user in logger.connected_users if user['player'] == player_name), None)
                if user_info and user_info["player"] not in curr_alloc_users:
                    # Add to allocated forces
                    logger.alloc_users.append(user_info)
                    allocated_forces_listbox.insert(tk.END, f"{user_info['player']} - Zone: {user_info['zone']}")
        except Exception as e:
            logger.log(f"⚠️ ERROR allocate_selected_users(): {e.__class__.__name__} - {e}")

    def allocate_all_users() -> None:
        """Allocate all Connected Users to Allocated Forces if not already in."""
        try:
            curr_alloc_users = [user["player"] for user in logger.alloc_users]
            for conn_user in logger.connected_users:
                if conn_user["player"] not in curr_alloc_users:
                    # Add to allocated forces
                    logger.alloc_users.append(conn_user)
                    allocated_forces_listbox.insert(tk.END, f"{conn_user['player']} - Zone: {conn_user['zone']}")
        except Exception as e:
            logger.log(f"⚠️ ERROR allocate_all_users(): {e.__class__.__name__} - {e}")

    def update_allocated_forces() -> None:
        """Update the status of users in the allocated forces list."""
        try:
            for index in range(allocated_forces_listbox.size()):
                item_text = allocated_forces_listbox.get(index)
                # Extract the player's name
                player_name = item_text.split(" - ")[0]
                user = next((user for user in logger.connected_users if user['player'] == player_name), None)
                # Remove allocated user
                del logger.alloc_users[index]
                allocated_forces_listbox.delete(index)
                # Only re-add user if they are currently connected
                if user:
                    logger.alloc_users.insert(index, user)
                    allocated_forces_listbox.insert(index, f"{user['player']} - Zone: {user['zone']}")
                    # Change text color of allocated users based on status
                    if user['status'] == "dead":
                        allocated_forces_listbox.itemconfig(index, {'fg': 'red'})
                    elif user['status'] == "alive":
                        allocated_forces_listbox.itemconfig(index, {'fg': 'green'})
        except Exception as e:
            logger.log(f"⚠️ ERROR update_allocated_forces(): {e.__class__.__name__} - {e}")

    # Refresh User List Function
    def refresh_user_list(active_users) -> None:
        """Refresh the connected users list and update allocated forces based on status."""
        print(f"Active users: {active_users}")
        try:
            # Remove any dupes and sort alphabetically
            no_dupes = [dict(t) for t in {tuple(user.items()) for user in active_users}]
            logger.connected_users = sorted(no_dupes, key=lambda user: user['player'])
            # Update Connected Users Listbox
            connected_users_listbox.delete(0, tk.END)
            for user in logger.connected_users:
                connected_users_listbox.insert(tk.END, user['player'])
            # Update Allocated Forces Listbox
            update_allocated_forces()
        except Exception as e:
            logger.log(f"⚠️ ERROR refresh_user_list(): {e.__class__.__name__} - {e}")

    # Attach the refresh_user_list function to the logger
    logger.refresh_user_list = refresh_user_list

    def check_for_cm_updates():
        """
        Checks the update_queue for new commander data and refreshes the user list.
        This method should be called periodically from the Tkinter main loop.
        """
        if not update_queue.empty():
            active_commanders = update_queue.get()
            logger.refresh_user_list(active_commanders)

        # Check again after a short delay
        commander_window.after(1000, check_for_cm_updates)  # Run every second

    # Assuming commander_window is your Tkinter window object
    commander_window.after(1000, check_for_cm_updates)

    def clear_listboxes():
        """Cleanup listboxes when disconnected."""
        logger.connected_users.clear()
        logger.alloc_users.clear()
        connected_users_listbox.delete(0, tk.END)
        allocated_forces_listbox.delete(0, tk.END)

