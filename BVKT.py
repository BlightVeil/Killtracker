import os
import json
import psutil
import requests
import threading
import webbrowser
import tkinter as tk
from tkinter import scrolledtext
from tkinter.font import Font
from tkinter import messagebox
import sys
from packaging import version
import time
import datetime

local_version = "7.0"
api_key = {"value": None}

global_game_mode = "Nothing"
global_active_ship = "N/A"
global_active_ship_id = "N/A"
global_player_geid = "N/A"

global_ship_list = [
    'DRAK', 'ORIG', 'AEGS', 'ANVL', 'CRUS', 'BANU', 'MISC',
    'KRIG', 'XNAA', 'ARGO', 'VNCL', 'ESPR', 'RSI', 'CNOU',
    'GRIN', 'TMBL', 'GAMA'
]

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
        headers = {'User-Agent': 'Killtracker/1.1'}
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

class EventLogger:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def log(self, message):
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, message + "\n")
        self.text_widget.config(state=tk.DISABLED)
        self.text_widget.see(tk.END)
        
def show_loading_animation(logger, app):
    for dots in [".","..", "..."]:
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

def set_player_zone(line, logger):
    global global_active_ship
    global global_active_ship_id
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

def validate_api_key(api_key, player_name):
    url = "http://38.46.216.78:25966/validateKey"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    data = {
        "api_key": api_key,
        "player_name": rsi_handle  # Include the player name
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return True  # Success
        else:
            return False  # Failure
    except requests.RequestException as e:
        print(f"API Key validation error: {e}")
        return False

def save_api_key(key):
    try:
        with open("killtracker_key.cfg", "w") as f:
            f.write(key)
        api_key["value"] = key  # Make sure to save the key in the global api_key dictionary as well
        logger.log(f"API key saved successfully: {key}")
    except Exception as e:
        logger.log(f"Error saving API key: {e}")

# Activate the API key by sending it to the server
def activate_key(key_entry):
    entered_key = key_entry.get().strip()  # Access key_entry here
    if entered_key:
        log_file_location = set_sc_log_location()  # Assuming this is defined elsewhere
        if log_file_location:
            player_name = get_player_name(log_file_location)  # Retrieve the player name
            if player_name:
                if validate_api_key(entered_key, player_name):  # Pass both the key and player name
                    save_api_key(entered_key)  # Save the key for future use
                    logger.log("Key activated and saved. Servitor connection established.")
                else:
                    logger.log("Invalid key or player name. Please enter a valid API key.")
            else:
                logger.log("RSI Handle not found. Please ensure the game is running and the log file is accessible.")
        else:
            logger.log("Log file location not found.")
    else:
        logger.log("No key entered. Please input a valid key.")

def get_player_name(log_file_location):
    # Retrieve the RSI handle using the existing function
    rsi_handle = find_rsi_handle(log_file_location)
    if not rsi_handle:
        print("Error: RSI handle not found.")
        return None
    return rsi_handle

# Load existing key from the file
def load_existing_key():
    try:
        with open("killtracker_key.cfg", "r") as f:
            entered_key = f.readline().strip()
            if entered_key:
                api_key["value"] = entered_key
                logger.log("Existing key loaded. Attempting to establish Servitor connection...")
                if validate_api_key(entered_key):
                    logger.log("Servitor connection established.")
                else:
                    logger.log("Invalid key. Please input a valid key.")
            else:
                logger.log("No valid key found. Please enter a key.")
    except FileNotFoundError:
        logger.log("No existing key found. Please enter a valid key.")

# Trigger kill event
def parse_kill_line(line, target_name, logger):
    print(f"Current API Key: {api_key['value']}")

    if not check_exclusion_scenarios(line, logger):
        return

    split_line = line.split(' ')

    kill_time = split_line[0].strip('\'')
    killed = split_line[5].strip('\'')
    killed_zone = split_line[9].strip('\'')
    killer = split_line[12].strip('\'')
    weapon = split_line[15].strip('\'')

    if killed == killer or killer.lower() == "unknown" or killed == target_name:
        logger.log("You have fallen in the service of BlightVeil.")
        return

    event_message = f"You have killed {killed},"
    logger.log(event_message)

    json_data = {
        'player': target_name,
        'victim': killed,
        'time': kill_time,
        'zone': killed_zone,
        'weapon': weapon,
        'rsi_profile': f"https://robertsspaceindustries.com/citizens/{killed}",
        'game_mode': global_game_mode,
        'client_ver': "7.0",
        'killers_ship': global_active_ship,
    }

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
    except requests.exceptions.RequestException as e:
        logger.log(f"Error sending kill event: {e}")
        logger.log("Kill event will not be sent. Please ensure a valid key and try again.")

def read_existing_log(log_file_location, rsi_name):
    sc_log = open(log_file_location, "r")
    lines = sc_log.readlines()
    for line in lines:
        read_log_line(line, rsi_name, True, logger)

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
            try:
                url = update_message.split("Download it here: ")[-1]
                webbrowser.open(url)
            except Exception as e:
                print(f"Error opening GitHub link: {e}")

        update_label.bind("<Button-1>", open_github)

    if game_running:
        # API Key Input
        key_frame = tk.Frame(app, bg="#484759")
        key_frame.pack(pady=(10, 10))

        key_label = tk.Label(
            key_frame, text="Enter Key:", font=("Times New Roman", 12), fg="#ffffff", bg="#484759"
        )
        key_label.pack(side=tk.LEFT, padx=(0, 5))

        key_entry = tk.Entry(key_frame, width=30, font=("Times New Roman", 12))
        key_entry.pack(side=tk.LEFT)

        # API Status Label
        api_status_label = tk.Label(
            app,
            text="API Status: Not Validated",
            font=("Times New Roman", 12),
            fg="#ffffff",
            bg="#484759",
        )
        api_status_label.pack(pady=(10, 10))

        # Activate API Key
        def activate_key():
            entered_key = key_entry.get().strip()  # Access key_entry here
            if entered_key:
                log_file_location = set_sc_log_location()  # Assuming this is defined elsewhere
                if log_file_location:
                    player_name = get_player_name(log_file_location)
                    if player_name:
                        if validate_api_key(entered_key, player_name):  # Pass both the key and player name
                            save_api_key(entered_key)  # Save the key for future use
                            logger.log("Key activated and saved. Servitor connection established.")
                            api_status_label.config(text="API Status: Valid (Expires in 72 hours)", fg="green")
                            start_api_key_countdown(entered_key, api_status_label)
                        else:
                            logger.log("Invalid key. Please enter a valid API key.")
                            api_status_label.config(text="API Status: Invalid", fg="red")
                    else:
                        logger.log("RSI Handle not found. Please ensure the game is running and the log file is accessible.")
                        api_status_label.config(text="API Status: Error", fg="yellow")
                else:
                    logger.log("Log file location not found.")
                    api_status_label.config(text="API Status: Error", fg="yellow")
            else:
                logger.log("No key entered. Please input a valid key.")
                api_status_label.config(text="API Status: Invalid", fg="red")

        activate_button = tk.Button(
            key_frame,
            text="Activate",
            font=("Times New Roman", 12),
            command=activate_key,
            bg="#000000",
            fg="#ffffff",
        )
        activate_button.pack(side=tk.LEFT, padx=(5, 0))

        # Load Existing Key
        def load_existing_key():
            try:
                with open("killtracker_key.cfg", "r") as f:
                    entered_key = f.readline().strip()
                    if entered_key:
                        api_key["value"] = entered_key  # Assign the loaded key
                        logger.log(f"Existing key loaded: {entered_key}. Attempting to establish Servitor connection...")
                        if validate_api_key(entered_key, get_player_name(set_sc_log_location())):  # Validate with player name
                            logger.log("Servitor connection established.")
                            api_status_label.config(text="API Status: Valid (Expires in 72 hours)", fg="green")
                            start_api_key_countdown(entered_key, api_status_label)
                        else:
                            logger.log("Invalid key. Please input a valid key.")
                            api_status_label.config(text="API Status: Invalid", fg="red")
                    else:
                        logger.log("No valid key found. Please enter a key.")
                        api_status_label.config(text="API Status: Invalid", fg="red")
            except FileNotFoundError:
                logger.log("No existing key found. Please enter a valid key.")
                api_status_label.config(text="API Status: Invalid", fg="red")

        load_key_button = tk.Button(
            key_frame,
            text="Load Existing Key",
            font=("Times New Roman", 12),
            command=load_existing_key,
            bg="#000000",
            fg="#ffffff",
        )
        load_key_button.pack(side=tk.LEFT, padx=(5, 0))

        # Log Display
        text_area = scrolledtext.ScrolledText(
            app, wrap=tk.WORD, width=80, height=20, state=tk.DISABLED, bg="#282a36", fg="#f8f8f2", font=("Consolas", 12)
        )
        text_area.pack(padx=10, pady=10)

        logger = EventLogger(text_area)

    else:
        # Relaunch Message
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

def start_api_key_countdown(api_key, api_status_label):
    """
    Function to start the countdown for the API key's expiration, refreshing expiry data periodically.
    """
    def update_countdown():
        expiration_time = get_api_key_expiration_time(api_key)  # Fetch latest expiration time
        if not expiration_time:
            api_status_label.config(text="API Status: Expired", fg="red")
            return

        def countdown():
            remaining_time = expiration_time - datetime.datetime.utcnow()
            if remaining_time.total_seconds() > 0:
                hours, remainder = divmod(remaining_time.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                countdown_text = f"API Status: Valid (Expires in {remaining_time.days}d {hours}h {minutes}m {seconds}s)"
                api_status_label.config(text=countdown_text, fg="green")
                api_status_label.after(1000, countdown)  # Update every second
            else:
                api_status_label.config(text="API Status: Expired", fg="red")

        countdown()

        # Refresh expiration time every 60 seconds to stay in sync with the server
        api_status_label.after(60000, update_countdown)

    update_countdown()

def get_api_key_expiration_time(api_key):
    """
    Retrieve the expiration time for the API key from the validation server.
    """
    url = "http://38.46.216.78:25966/validateKey"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    data = {
        "player_name": rsi_handle
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            response_data = response.json()
            expiration_time_str = response_data.get("expires_at")
            if expiration_time_str:
                return datetime.datetime.strptime(expiration_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            else:
                print("Error: 'expires_at' not found in response")
        else:
            print("Error fetching expiration time:", response.json().get("error", "Unknown error"))
    except requests.RequestException as e:
        print(f"API request error: {e}")

    # Fallback: Expire immediately if there's an error
    return None

def read_log_line(line, rsi_name, upload_kills, logger):
    if -1 != line.find("<Context Establisher Done>"):
        set_game_mode(line, logger)
    elif -1 != line.find(rsi_name):
        if -1 != line.find("OnEntityEnterZone"):
            set_player_zone(line, logger)
        if -1 != line.find("CActor::Kill") and not check_substring_list(line, ignore_kill_substrings) and upload_kills:
            parse_kill_line(line, rsi_name, logger)
    elif -1 != line.find("CPlayerShipRespawnManager::OnVehicleSpawned") and (
            "SC_Default" != global_game_mode) and (-1 != line.find(global_player_geid)):
        set_ac_ship(line, logger)
    elif ((-1 != line.find("<Vehicle Destruction>")) or (
            -1 != line.find("<local client>: Entering control state dead"))) and (
            -1 != line.find(global_active_ship_id)):
        destroy_player_zone(line, logger)

def tail_log(log_file_location, rsi_name, logger):
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
        read_log_line(line, rsi_name, False, logger)

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
            read_log_line(line, rsi_name, True, logger)

def start_tail_log_thread(log_file_location, rsi_name, logger):
    """Start the log tailing in a separate thread."""
    thread = threading.Thread(target=tail_log, args=(log_file_location, rsi_name, logger))
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
            if rsi_handle:
                start_tail_log_thread(log_file_location, rsi_handle, logger)
    
    # Initiate auto-shutdown after 72 hours (72 * 60 * 60 seconds)
    if logger:
        auto_shutdown(app, 72 * 60 * 60, logger)  # Pass logger only if initialized
    else:
        auto_shutdown(app, 72 * 60 * 60)  # Fallback without logger

    app.mainloop()
