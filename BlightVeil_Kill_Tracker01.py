import os
import json
import psutil
import requests
import threading
import tkinter as tk
from tkinter import scrolledtext
from tkinter.font import Font
from tkinter import messagebox
import sys
from packaging import version
import time

local_version = "1.0"
api_key = {"value": None}

def resource_path(relative_path):
    """ Get the absolute path to the resource (works for PyInstaller .exe). """
    try:
        base_path = sys._MEIPASS  
    except AttributeError:
        base_path = os.path.abspath(".")  
    return os.path.join(base_path, relative_path)

def check_for_updates():
    """Check for updates using the GitHub API."""
    github_api_url = "https://api.github.com/repos/BlightVeil/Killtracker/releases/latest"

    try:
        headers = {'User-Agent': 'Killtracker/1.0'}
        response = requests.get(github_api_url, headers=headers, timeout=5)

        if response.status_code == 200:
            release_data = response.json()
            remote_version = release_data.get("tag_name", "v1.0").strip("v")
            download_url = release_data.get("html_url", "")

            if version.parse(local_version) < version.parse(remote_version):
                return f"Update available: {remote_version}. Download it here: {download_url}"
        else:
            print(f"GitHub API error: {response.status_code}")
    except Exception as e:
        print(f"Error checking for updates: {e}")
    return None

global_game_mode = "Nothing"
global_active_ship = "N/A"
global_active_ship_id = "N/A"
global_player_geid = "N/A"
global_heartbeat_active = False
global_rsi_handle = ""


global_ship_list = [
    'DRAK', 'ORIG', 'AEGS', 'ANVL', 'CRUS', 'BANU', 'MISC',
    'KRIG', 'XNAA', 'ARGO', 'VNCL', 'ESPR', 'RSI', 'CNOU',
    'GRIN', 'TMBL', 'GAMA'
]

class EventLogger:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def log(self, message):
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, message + "\n")
        self.text_widget.config(state=tk.DISABLED)
        self.text_widget.see(tk.END)
        
def show_loading_animation(logger, app):
    for dots in ["..", "..."]:
        logger.log(dots)
        app.update_idletasks()
        time.sleep(0.2)


def destroy_player_zone(line, logger):
    global global_active_ship
    global global_active_ship_id
    if ("N/A" != global_active_ship) or ("N/A" != global_active_ship_id):
        print(f"Ship Destroyed: {global_active_ship} with ID: {global_active_ship_id}")
        global_active_ship = "N/A"
        global_active_ship_id = "N/A"


def set_ac_ship(line, logger):
    global global_active_ship
    global_active_ship = line.split(' ')[5][1:-1]
    print("Player has entered ship: ", global_active_ship)


def post_heartbeat_enter_ship_event(rsi_handle, player_ship, logger):
    """Update the ship and set player to alive with heartbeat!"""
    json_data = {
        'is_heartbeat': True,
        'player': rsi_handle,
        'zone': player_ship,
        'client_ver': "7.0",
        'status': "alive",  # Report status as 'alive'
    }

    headers = {
        'content-type': 'application/json',
        'Authorization': api_key["value"] if api_key["value"] else ""
    }

    try:
        response = requests.post(
            "http://38.46.216.78:25966/validateKey",
            headers=headers,
            data=json.dumps(json_data),
            timeout=5
        )
        if response.status_code != 200:
            logger.log(f"Failed to report ship status event: {response.status_code}.")
    except Exception as e:
        logger.log(f"Error reporting ship status event: {e}")


def set_player_zone(line, logger):
    global global_active_ship
    global global_active_ship_id
    global global_heartbeat_active
    global global_rsi_handle
    line_index = line.index("-> Entity ") + len("-> Entity ")
    if 0 == line_index:
        print("Active Zone Change: ", global_active_ship)
        global_active_ship = "N/A"
        return
    potential_zone = line[line_index:].split(' ')[0]
    potential_zone = potential_zone[1:-1]
    for x in global_ship_list:
        if potential_zone.startswith(x):
            global_active_ship = potential_zone[:potential_zone.rindex('_')]
            global_active_ship_id = potential_zone[potential_zone.rindex('_') + 1:]
            print(f"Active Zone Change: {global_active_ship} with ID: {global_active_ship_id}")
            if global_heartbeat_active:
                post_heartbeat_enter_ship_event(global_rsi_handle, global_active_ship, logger)
            return


def check_if_process_running(process_name):
    """ Check if a process is running by name. """
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        if process_name.lower() in proc.info['name'].lower():
            return proc.info['exe']
    return None


def find_game_log_in_directory(directory):
    """ Search for Game.log in the directory and its parent directory. """
    game_log_path = os.path.join(directory, 'Game.log')
    if os.path.exists(game_log_path):
        print(f"Found Game.log in: {directory}")
        return game_log_path
    # If not found in the same directory, check the parent directory
    parent_directory = os.path.dirname(directory)
    game_log_path = os.path.join(parent_directory, 'Game.log')
    if os.path.exists(game_log_path):
        print(f"Found Game.log in parent directory: {parent_directory}")
        return game_log_path
    return None


def set_sc_log_location():
    """ Check for RSI Launcher and Star Citizen Launcher, and set SC_LOG_LOCATION accordingly. """
    # Check if RSI Launcher is running
    rsi_launcher_path = check_if_process_running("RSI Launcher")
    if not rsi_launcher_path:
        print("RSI Launcher not running.")
        return None

    print("RSI Launcher running at:", rsi_launcher_path)

    # Check if Star Citizen Launcher is running
    sc_launcher_path = check_if_process_running("StarCitizen")
    if not sc_launcher_path:
        print("Star Citizen Launcher not running.")
        return None

    print("Star Citizen Launcher running at:", sc_launcher_path)

    # Search for Game.log in the folder next to StarCitizen_Launcher.exe
    star_citizen_dir = os.path.dirname(sc_launcher_path)
    print(f"Searching for Game.log in directory: {star_citizen_dir}")
    log_path = find_game_log_in_directory(star_citizen_dir)

    if log_path:
        print("Setting SC_LOG_LOCATION to:", log_path)
        os.environ['SC_LOG_LOCATION'] = log_path
        return log_path
    else:
        print("Game.log not found in expected locations.")
        return None
        
# Substrings to ignore
ignore_kill_substrings = [
    'PU_Pilots',
    'NPC_Archetypes',
    'PU_Human',
    'kopion',
    'marok',
]

def check_substring_list(line, substring_list):
    """
    Check if any substring from the list is present in the given line.
    """
    for substring in substring_list:
        if substring.lower() in line.lower():
            return True
    return False

def check_exclusion_scenarios(line, logger):
    global global_game_mode
    if global_game_mode == "EA_FreeFlight" and -1 != line.find("Crash"):
        print("Probably a ship reset, ignoring kill!")
        return False
    return True


def post_heartbeat(rsi_handle, logger):
    global global_heartbeat_active
    global global_active_ship
    while True:
        time.sleep(5)

        # Prepare the data for the Discord bot
        if "N/A" == global_active_ship or "" == global_active_ship:
            status = "dead"
        else:
            status = "alive"

        json_data = {
            'is_heartbeat': True,
            'player': rsi_handle,
            'zone': global_active_ship,
            'client_ver': "7.0",
            'status': status,  # Report status as 'alive'
        }

        heartbeat_url = "http://38.46.216.78:25966/validateKey"
        headers = {
            'content-type': 'application/json',
            'Authorization': api_key["value"] if api_key["value"] else ""
        }

        if not api_key["value"]:
            logger.log("Heartbeat will not be sent. Enter valid key to establish connection with Servitor...")
            global_heartbeat_active = False
            return

        # Send heartbeat to Servitor. Should never reach this until API key is already validated.
        try:
            response = requests.post(heartbeat_url, headers=headers, data=json.dumps(json_data), timeout=5)
            if response.status_code != 200:
                logger.log(f"Commander connectivity error: {response.status_code}.")
            if response.status_code == 200 and not global_heartbeat_active:
                logger.log(f"Connected to commander: {response.status_code}.")
                global_heartbeat_active = True

        except Exception as e:
            global_heartbeat_active = False
            logger.log(f"Error connecting to Servitor: {e}")
            return


def post_heartbeat_death_event(target_name, killed_zone, logger):
    """Currently only support death events from the player!"""
    json_data = {
        'is_heartbeat': True,
        'player': target_name,
        'zone': killed_zone,
        'client_ver': "7.0",
        'status': "dead",  # Report status as 'dead'
    }

    headers = {
        'content-type': 'application/json',
        'Authorization': api_key["value"] if api_key["value"] else ""
    }

    try:
        response = requests.post(
            "http://38.46.216.78:25966/validateKey",
            headers=headers,
            data=json.dumps(json_data),
            timeout=5
        )
        if response.status_code != 200:
            logger.log(f"Failed to report death event: {response.status_code}.")
    except Exception as e:
        logger.log(f"Error reporting death event: {e}")


def post_kill_event(json_data, logger):
    headers = {
        'content-type': 'application/json',
        'Authorization': api_key["value"] if api_key["value"] else ""
    }
    if not api_key["value"]:
        logger.log("Kill event will not be sent. Enter valid key to establish connection with Servitor...")
        return

    try:
        response = requests.post(
            "http://38.46.216.78:25966/reportKill",
            headers=headers,
            data=json.dumps(json_data)
        )
        if response.status_code == 200:
            logger.log("and brought glory to the Veil.")
        else:
            logger.log(f"Servitor connectivity error: {response.status_code}.")
            logger.log("Relaunch BV Kill Tracker and reconnect with a new Key.")
    except Exception as e:
        show_loading_animation(logger, app)
        logger.log(f"Kill event will not be sent. Enter valid key to establish connection with Servitor...")


def parse_kill_line(line, target_name, logger):
    """
    Parses a kill line from the log and handles player kills, deaths, and related events.
    """
    global global_active_ship
    global player_status  # Add a global status variable to track player's state
    player_status = "alive"  # Default status is alive

    if not check_exclusion_scenarios(line, logger):
        return

    split_line = line.split(' ')

    kill_time = split_line[0].strip('\'')
    killed = split_line[5].strip('\'')
    killed_zone = split_line[9].strip('\'')
    killer = split_line[12].strip('\'')
    weapon = split_line[15].strip('\'')
    rsi_profile = f"https://robertsspaceindustries.com/citizens/{killed}"

    if killed == killer or killer.lower() == "unknown" or killed == target_name:
        # Log a message for the player's own death
        show_loading_animation(logger, app)
        logger.log("You have fallen in the service of BlightVeil.")

        # Send death-event to the server via heartbeat
        post_heartbeat_death_event(target_name, killed_zone, logger)
        destroy_player_zone(line, logger)
        return

    # Log a custom message for a successful kill
    show_loading_animation(logger, app)
    event_message = f"You have killed {killed},"
    logger.log(event_message)

    # Prepare the data for the Discord bot
    json_data = {
        'is_heartbeat': False,
        'player': target_name,
        'victim': killed,
        'time': kill_time,
        'zone': killed_zone,
        'weapon': weapon,
        'rsi_profile': rsi_profile,
        'game_mode': global_game_mode,
        'client_ver': "7.0",
        'killers_ship': global_active_ship,
    }
    post_kill_event(json_data, logger)


def read_existing_log(log_file_location, rsi_handle):
    sc_log = open(log_file_location, "r")
    lines = sc_log.readlines()
    for line in lines:
        read_log_line(line, rsi_handle, True, logger)


def find_rsi_handle(log_file_location):
    acct_str = "<Legacy login response> [CIG-net] User Login Success"
    sc_log = open(log_file_location, "r")
    lines = sc_log.readlines()
    for line in lines:
        if -1 != line.find(acct_str):
            line_index = line.index("Handle[") + len("Handle[")
            if 0 == line_index:
                print("RSI_HANDLE: Not Found!")
                exit()
            potential_handle = line[line_index:].split(' ')[0]
            return potential_handle[0:-1]
    return None


def find_rsi_geid(log_file_location):
    global global_player_geid
    acct_kw = "AccountLoginCharacterStatus_Character"
    sc_log = open(log_file_location, "r")
    lines = sc_log.readlines()
    for line in lines:
        if -1 != line.find(acct_kw):
            global_player_geid = line.split(' ')[11]
            print("Player geid: " + global_player_geid)
            return


def set_game_mode(line, logger):
    global global_game_mode
    global global_active_ship
    global global_active_ship_id
    split_line = line.split(' ')
    game_mode = split_line[8].split("=")[1].strip("\"")
    if game_mode != global_game_mode:
        global_game_mode = game_mode

    if "SC_Default" == global_game_mode:
        global_active_ship = "N/A"
        global_active_ship_id = "N/A"


def verify_key_with_heartbeat(entered_key):
    # Prepare the request
    heartbeat_url = "http://38.46.216.78:25966/validateKey"
    headers = {
        'content-type': 'application/json',
        'Authorization': entered_key,
    }

    # Send heartbeat to Servitor
    try:
        response = requests.post(heartbeat_url, headers=headers, timeout=5)
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("status") == "valid":
                api_key["value"] = entered_key
                logger.log("Servitor Connection Established.")
                logger.log("Go forth and KILL...")
            else:
                logger.log("Invalid key. Please input a valid key to establish connection with Servitor.")
        else:
            logger.log(f"Servitor connectivity error: {response.status_code}.")
    except Exception as e:
        logger.log(f"Error connecting to Servitor: {e}")


def load_existing_key(app, logger):
    """Handles loading an existing API key from the configuration file."""
    if os.path.exists("killtracker_key.cfg"):
        try:
            with open("killtracker_key.cfg", "r") as f:
                entered_key = f.readline().strip()
                if entered_key:
                    logger.log("Activating key...")
                    show_loading_animation(logger, app)
                    logger.log("Initiating Servitor Connection...")
                    logger.log(".")
                    app.update_idletasks()  # Ensure app is a valid Tkinter instance
                    time.sleep(0.5)
                    logger.log("..")
                    app.update_idletasks()
                    time.sleep(0.5)
                    logger.log("...")
                    verify_key_with_heartbeat(entered_key)

                else:
                    logger.log("Error: No key detected in file. Input valid key to establish connection with Servitor.")
        except Exception as e:
            logger.log(f"Error in load_existing_key: {e}")
    else:
        logger.log("No key file found. Please input a valid key to establish connection with Servitor.")


def activate_key(app, key_entry, logger):
    """Handles activating a new API key entered by the user."""
    try:
        entered_key = key_entry.get().strip()
        if entered_key:
            logger.log("Activating key...")
            show_loading_animation(logger, app)
            logger.log("Initiating Servitor Connection...")
            logger.log(".")
            app.update_idletasks()
            time.sleep(0.5)
            logger.log("..")
            app.update_idletasks()
            time.sleep(0.5)
            logger.log("...")
            verify_key_with_heartbeat(entered_key)
            f = open("killtracker_key.cfg", "w")
            f.write(entered_key)

        else:
            logger.log("Error: No key detected. Input valid key to establish connection with Servitor.")
    except Exception as e:
        logger.log(f"Error in activate_key: {e}")

def setup_game_running_gui(app):
    """Setup GUI elements when the game is running."""
    key_frame = tk.Frame(app, bg="#484759")
    key_frame.pack(pady=(10, 10))

    key_label = tk.Label(
        key_frame, text="Enter Key:", font=("Times New Roman", 12), fg="#ffffff", bg="#484759"
    )
    key_label.pack(side=tk.LEFT, padx=(0, 5))

    key_entry = tk.Entry(key_frame, width=30, font=("Times New Roman", 12))
    key_entry.pack(side=tk.LEFT)

    # Initialize logger here
    text_area = scrolledtext.ScrolledText(
        app, wrap=tk.WORD, width=80, height=20, state=tk.DISABLED, bg="#282a36", fg="#f8f8f2", font=("Consolas", 12)
    )
    text_area.pack(padx=10, pady=10)

    logger = EventLogger(text_area)

    activate_button = tk.Button(
        key_frame,
        text="Activate",
        font=("Times New Roman", 12),
        command=lambda: activate_key(app, key_entry, logger),  # Pass logger here
        bg="#000000",
        fg="#ffffff",
    )
    activate_button.pack(side=tk.LEFT, padx=(5, 0))

    load_key_button = tk.Button(
        key_frame,
        text="Load Existing Key",
        font=("Times New Roman", 12),
        command=lambda: load_existing_key(app, logger),  # Pass logger here
        bg="#000000",
        fg="#ffffff",
    )
    load_key_button.pack(side=tk.LEFT, padx=(5, 0))

    start_hearbeat_button = tk.Button(
        key_frame,
        text="Connect to Commander",
        font=("Times New Roman", 12),
        command=lambda: start_heartbeat_thread(logger),  # Pass logger here
        bg="#000000",
        fg="#ffffff",
    )
    start_hearbeat_button.pack(side=tk.LEFT, padx=(5, 0))

    # Commander Mode Button
    commander_mode_button = tk.Button(
        app,
        text="Commander Mode",
        font=("Times New Roman", 12),
        command=lambda: open_commander_mode(logger),
        bg="#000000",
        fg="#ffffff",
    )
    commander_mode_button.pack(pady=(10, 10)) 

    return logger
    
def setup_gui(game_running):
    app = tk.Tk()
    app.title("BlightVeil Kill Tracker")
    app.geometry("800x800")
    app.configure(bg="#484759") 

    # Set the icon
    try:
        icon_path = resource_path("BlightVeil.ico")
        if os.path.exists(icon_path):
            app.iconbitmap(icon_path)
            print(f"Icon loaded successfully from: {icon_path}")
        else:
            print(f"Icon not found at: {icon_path}")
    except Exception as e:
        print(f"Error setting icon: {e}")

    # Add Banner
    try:
        banner_path = resource_path("BlightVeilBanner.png")  
        banner_image = tk.PhotoImage(file=banner_path)
        banner_label = tk.Label(app, image=banner_image, bg="#484759")
        banner_label.image = banner_image 
        banner_label.pack(pady=(0, 10))  
    except Exception as e:
        print(f"Error loading banner image: {e}")
        
    # Check for Updates
    update_message = check_for_updates()
    if update_message:
        update_label = tk.Label(
            app,
            text=update_message,
            font=("Times New Roman", 12),
            fg="#ff5555",
            bg="#484759",
            wraplength=700,
            justify="center",
            cursor="hand2",
        )
        update_label.pack(pady=(10, 10))

        def open_github(event):
            import webbrowser
            try:
                url = update_message.split("Download it here: ")[-1]
                webbrowser.open(url)
            except Exception as e:
                print(f"Error opening GitHub link: {e}")

        update_label.bind("<Button-1>", open_github)

    # Game Running or Not
    if game_running:
        logger = setup_game_running_gui(app)  
    else:
        message_label = tk.Label(
            app,
            text="You must launch Star Citizen before starting the tracker.\n\nPlease close this window, launch Star Citizen, and relaunch the BV Kill Tracker. ",
            font=("Times New Roman", 14),
            fg="#000000",
            bg="#484759",
            wraplength=700,
            justify="center",
        )
        message_label.pack(pady=(50, 10))
        logger = None

    # Footer
    footer = tk.Frame(app, bg="#3e3b4d", height=30)
    footer.pack(side=tk.BOTTOM, fill=tk.X)

    footer_text = tk.Label(
        footer,
        text="BlightVeil Kill Tracker - Credits: CyberBully-Actual, BossGamer09, Holiday",
        font=("Times New Roman", 10),
        fg="#bcbcd8",
        bg="#3e3b4d",
    )
    footer_text.pack(pady=5)

    return app, logger
    
def open_commander_mode(logger):
    """
    Opens a new window for Commander Mode, displaying connected users and allocated forces.
    Includes functionality for moving users to the allocated forces list and handling status changes.
    """
    commander_window = tk.Toplevel()
    commander_window.title("Commander Mode")
    commander_window.geometry("800x600")
    commander_window.configure(bg="#484759")

    # Search bar for filtering connected users
    search_var = tk.StringVar()
    search_bar = tk.Entry(commander_window, textvariable=search_var, font=("Consolas", 12), width=30)
    search_bar.pack(pady=(10, 0))

    # Connected Users Listbox
    connected_users_frame = tk.Frame(commander_window, bg="#484759")
    connected_users_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 5))

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
    allocated_forces_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 10))

    allocated_forces_label = tk.Label(
        allocated_forces_frame, text="Allocated Forces", font=("Times New Roman", 12), fg="#ffffff", bg="#484759"
    )
    allocated_forces_label.pack()

    allocated_forces_listbox = tk.Listbox(
        allocated_forces_frame, 
        width=40,
        height=20,
        bg="#282a36",
        fg="#00ff00",  # Default to green (alive)
        font=("Consolas", 12)
    )
    allocated_forces_listbox.pack(fill=tk.BOTH, expand=True)

    # Add Button
    add_button = tk.Button(
        commander_window,
        text=">>>",
        font=("Times New Roman", 12),
        command=lambda: allocate_selected_users(),
        bg="#000000",
        fg="#ffffff",
    )
    add_button.pack(pady=(0, 10))

    # Close Button
    close_button = tk.Button(
        commander_window,
        text="Close",
        font=("Times New Roman", 12),
        command=commander_window.destroy,
        bg="#000000",
        fg="#ffffff",
    )
    close_button.pack(pady=(10, 10))

    # Search Functionality
    def search_users(*args):
        search_query = search_var.get().lower()
        connected_users_listbox.delete(0, tk.END)
        for user in logger.connected_users:
            if search_query in user['player'].lower():
                connected_users_listbox.insert(tk.END, user['player'])

    search_var.trace("w", search_users)

    # Allocate Selected Users to Allocated Forces
    def allocate_selected_users():
        selected_indices = connected_users_listbox.curselection()
        for index in selected_indices:
            player_name = connected_users_listbox.get(index)
            # Find the full user info
            user_info = next((user for user in logger.connected_users if user['player'] == player_name), None)
            if user_info:
                # Add to allocated forces
                allocated_forces_listbox.insert(tk.END, f"{user_info['player']} - Zone: {user_info['zone']}")

    # Update Allocated Forces Based on Status
    def update_allocated_forces(active_users):
        """
        Update the colors of users in the allocated forces list based on their status.
        """
        for index in range(allocated_forces_listbox.size()):
            item_text = allocated_forces_listbox.get(index)
            # Extract the player's name
            player_name = item_text.split(" - ")[0]
            user = next((user for user in active_users if user['player'] == player_name), None)
            if user:
                # Change text color based on status
                if user['status'] == "dead":
                    allocated_forces_listbox.itemconfig(index, {'fg': 'red'})
                elif user['status'] == "alive":
                    allocated_forces_listbox.itemconfig(index, {'fg': 'green'})

    # Refresh User List Function
    def refresh_user_list(active_users):
        """
        Refresh the connected users list and update allocated forces based on status.
        """
        # Update Connected Users Listbox
        connected_users_listbox.delete(0, tk.END)
        logger.connected_users = active_users
        for user in active_users:
            connected_users_listbox.insert(tk.END, user['player'])

        # Update Allocated Forces Colors
        update_allocated_forces(active_users)

    # Attach the refresh_user_list function to the logger
    logger.refresh_user_list = refresh_user_list


# Event checking logic. Look for substrings, do stuff based on what we find.
def read_log_line(line, rsi_handle, upload_kills, logger):
    if -1 != line.find("<Context Establisher Done>"):
        set_game_mode(line, logger)
    elif -1 != line.find("CPlayerShipRespawnManager::OnVehicleSpawned") and (
            "SC_Default" != global_game_mode) and (-1 != line.find(global_player_geid)):
        set_ac_ship(line, logger)
    elif ((-1 != line.find("<Vehicle Destruction>")) or (
            -1 != line.find("<local client>: Entering control state dead"))) and (
            -1 != line.find(global_active_ship_id)):
        destroy_player_zone(line, logger)
    elif -1 != line.find(rsi_handle):
        if -1 != line.find("OnEntityEnterZone"):
            set_player_zone(line, logger)
        if -1 != line.find("CActor::Kill") and not check_substring_list(line, ignore_kill_substrings) and upload_kills:
            parse_kill_line(line, rsi_handle, logger)


def tail_log(log_file_location, rsi_handle, logger):
    """Read the log file and display events in the GUI."""
    global global_game_mode, global_player_geid
    sc_log = open(log_file_location, "r")
    if sc_log is None:
        logger.log(f"No log file found at {log_file_location}.")
        return

    logger.log("Kill Tracking Initiated...")
    logger.log("Enter key to establish Servitor connection...")

    # Read all lines to find out what game mode player is currently, in case they booted up late.
    # Don't upload kills, we don't want repeating last sessions kills incase they are actually available.
    lines = sc_log.readlines()
    print("Loading old log (if available)! Kills shown will not be uploaded as they are stale.")
    for line in lines:
        read_log_line(line, rsi_handle, False, logger)

    # Main loop to monitor the log
    last_log_file_size = os.stat(log_file_location).st_size
    while True:
        where = sc_log.tell()
        line = sc_log.readline()
        if not line:
            time.sleep(1)
            sc_log.seek(where)
            if last_log_file_size > os.stat(log_file_location).st_size:
                sc_log.close()
                sc_log = open(log_file_location, "r")
                last_log_file_size = os.stat(log_file_location).st_size
        else:
            read_log_line(line, rsi_handle, True, logger)


def start_tail_log_thread(log_file_location, rsi_handle, logger):
    """Start the log tailing in a separate thread."""
    thread = threading.Thread(target=tail_log, args=(log_file_location, rsi_handle, logger))
    thread.daemon = True
    thread.start()


def start_heartbeat_thread(logger):
    """Start the heartbeat in a seperate thread"""
    global global_rsi_handle
    global global_heartbeat_active
    if global_heartbeat_active:
        logger.log("Already connected to commander!")
        return
    logger.log("Connecting to commander...")
    thread = threading.Thread(target=post_heartbeat, args=(global_rsi_handle, logger))
    thread.daemon = True
    thread.start()


def is_game_running():
    """Check if Star Citizen is running."""
    return check_if_process_running("StarCitizen") is not None


def auto_shutdown(app, delay_in_seconds, logger=None):
    def shutdown():
        time.sleep(delay_in_seconds) 
        if logger:
            logger.log("Application has been open for 72 hours. Shutting down in 60 seconds.") 
        else:
            print("Application has been open for 72 hours. Shutting down in 60 seconds.")  

        time.sleep(60)

        app.quit() 
        sys.exit(0) 

    # Run the shutdown logic in a separate thread
    shutdown_thread = threading.Thread(target=shutdown, daemon=True)
    shutdown_thread.start()


if __name__ == '__main__':
    game_running = is_game_running()

    app, logger = setup_gui(game_running)

    if game_running:
        # Start log monitoring in a separate thread
        log_file_location = set_sc_log_location()
        if log_file_location:
            rsi_handle = find_rsi_handle(log_file_location)
            find_rsi_geid(log_file_location)
            if rsi_handle:
                global_rsi_handle = rsi_handle
                start_tail_log_thread(log_file_location, rsi_handle, logger)
    
    # Initiate auto-shutdown after 72 hours (72 * 60 * 60 seconds)
    if logger:
        auto_shutdown(app, 72 * 60 * 60, logger)  # Pass logger only if initialized
    else:
        auto_shutdown(app, 72 * 60 * 60)  # Fallback without logger

    app.mainloop()
