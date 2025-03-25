import os
import sys
import json
import time
import psutil
import shutil
import random
import winsound
import datetime
import warnings
warnings.filterwarnings("ignore", message="Couldn't find ffmpeg or avconv")
import requests
import threading
import webbrowser
import tkinter as tk
from queue import Queue
from packaging import version
from tkinter import scrolledtext

# Directory for sounds
SOUNDS_FOLDER = "sounds"

local_version = "1.3"
api_key = {"value": None}
stop_event = threading.Event()
global_game_mode = "Nothing"
global_active_ship = "N/A"
global_active_ship_id = "N/A"
global_player_geid = "N/A"
global_rsi_handle = ""
anonymize_state = {"enabled": False}
global_commander_heartbeat_active = False
global_heartbeat_active = False
global global_heartbeat_daemon
update_queue = Queue()

# Ensure external sounds folder exists before doing anything else
os.makedirs(SOUNDS_FOLDER, exist_ok=True)  # Cleaner way to create folder if missing

global_ship_list = [
    'DRAK', 'ORIG', 'AEGS', 'ANVL', 'CRUS', 'BANU', 'MISC',
    'KRIG', 'XNAA', 'ARGO', 'VNCL', 'ESPR', 'RSI', 'CNOU',
    'GRIN', 'TMBL', 'GAMA'
]

def resource_path(relative_path):
    """ Get the absolute path to the resource (works for PyInstaller .exe and Nuitka .exe). """
    try:
        # When running in a frozen environment (compiled executable)
        base_path = sys._MEIPASS  
    except AttributeError:
        # When running in a normal Python environment (source code)
        base_path = os.path.abspath(".")  
    return os.path.join(base_path, relative_path)

# Folder where user places their sounds (next to the .exe when running a built version)
EXTERNAL_SOUNDS_FOLDER = os.path.join(os.getcwd(), "sounds")

SOUNDS_FOLDER = resource_path("sounds")

# Ensure the external sounds folder exists before doing anything else
os.makedirs(EXTERNAL_SOUNDS_FOLDER, exist_ok=True)
os.makedirs(SOUNDS_FOLDER, exist_ok=True)

def check_for_updates():
    """Check for updates using the GitHub API."""
    github_api_url = "https://api.github.com/repos/BlightVeil/Killtracker/releases/latest"

    try:
        headers = {'User-Agent': 'Killtracker/1.3'}
        response = requests.get(github_api_url, headers=headers, timeout=5)

        if response.status_code == 200:
            release_data = response.json()
            remote_version = release_data.get("tag_name", "v1.3").strip("v")
            download_url = release_data.get("html_url", "")

            if version.parse(local_version) < version.parse(remote_version):
                return f"Update available: {remote_version}. Download it here: {download_url}"
        else:
            print(f"GitHub API error: {response.status_code}")
    except Exception as e:
        print(f"Error checking for updates: {e}")
    return None

def monitor_game_state(log_file_location, rsi_name, logger):
    """ Continuously monitor the game state and manage log monitoring. """
    last_state = None  # Track last known game state

    while True:
        game_running = is_game_running()

        if game_running and last_state != True:  # Log only when transitioning to running
            logger.log("Star Citizen is running. Ignore API Key if Status Is Green")
            if not logger.is_monitoring:  # Ensure tailing thread is not running already
                start_tail_log_thread(log_file_location, rsi_name, logger)
                logger.is_monitoring = True

        elif not game_running and last_state != False:  # Log only when transitioning to stopped
            logger.log("Star Citizen has stopped. Pausing log monitoring...")
            logger.is_monitoring = False

        last_state = game_running  # Update last state
        time.sleep(5)  # Check every 5 seconds

def copy_sounds_to_target_folder():
    # Determine the location of the resources, using the extraction folder if it's running from a bundled .exe
    try:
        base_path = sys._MEIPASS  # For PyInstaller bundles
    except Exception:
        base_path = os.path.abspath(".")  # If running from source

    sounds_source = os.path.join(base_path, "sounds")
    sounds_target = os.path.join(os.getcwd(), "sounds")  # Using the current working directory

    # Ensure the target folder exists
    if not os.path.exists(sounds_target):
        os.makedirs(sounds_target)

    # Get the current files in the target folder
    existing_files = set(os.listdir(sounds_target))

    # Copy only the new .wav files from the source to the target folder
    try:
        for sound_file in os.listdir(sounds_source):
            if sound_file.endswith(".wav"):  # Filter for .wav files
                if sound_file not in existing_files:  # Skip already existing files
                    source_path = os.path.join(sounds_source, sound_file)
                    target_path = os.path.join(sounds_target, sound_file)
                    if os.path.isfile(source_path):
                        shutil.copy(source_path, target_path)
                        print(f"Copied new sound: {sound_file} to {sounds_target}")
    except Exception as e:
        print(f"Error copying sounds: {e}")        

def copy_new_sounds():
    """Copy any new files from the external sounds folder to the program's sounds folder."""
    if not os.path.exists(EXTERNAL_SOUNDS_FOLDER):
        print(f"External sounds folder not found: {EXTERNAL_SOUNDS_FOLDER}")
        return

    # Ensure the program's sounds folder exists
    os.makedirs(SOUNDS_FOLDER, exist_ok=True)

    # Get the list of existing files in the program's sounds folder
    existing_files = set(os.listdir(SOUNDS_FOLDER))

    try:
        for sound_file in os.listdir(EXTERNAL_SOUNDS_FOLDER):
            source_path = os.path.join(EXTERNAL_SOUNDS_FOLDER, sound_file)
            target_path = os.path.join(SOUNDS_FOLDER, sound_file)

            # Check if it's a file and if it's not already copied
            if os.path.isfile(source_path) and sound_file not in existing_files:
                shutil.copy(source_path, target_path)
                print(f"Copied new sound: {sound_file} to {SOUNDS_FOLDER}")

    except Exception as e:
        print(f"Error copying sounds: {e}")

def get_all_sounds():
    """Fetch only .wav sounds from the sounds folder."""
    if not os.path.exists(SOUNDS_FOLDER):
        print("❌ Sounds folder not found!")
        return []
    
    return [
        os.path.join(SOUNDS_FOLDER, f) for f in os.listdir(SOUNDS_FOLDER) 
        if f.endswith(".wav")
    ]
    
def play_random_sound():
    """Play a single random .wav file from the sounds folder."""
    sounds = get_all_sounds()
    if sounds:
        sound_to_play = random.choice(sounds)  # Select a random sound
        try:
            logger.log(f"✅ Playing sound: {sound_to_play}")
            winsound.PlaySound(sound_to_play, winsound.SND_FILENAME)  # Play the selected sound
        except Exception as e:
            print(f"⚠️ Error playing sound {sound_to_play}: {e}")
    else:
        print("❌ No .wav sound files found.")

class EventLogger:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.is_monitoring = False
        self.connected_users = []
        self.alloc_users = []

    def log(self, message):
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, message + "\n")
        self.text_widget.config(state=tk.DISABLED)
        self.text_widget.see(tk.END)
        
def async_loading_animation(logger, app):
    def animate():
        for dots in [".", "..", "..."]:
            logger.log(dots)
            app.update_idletasks()
            time.sleep(0.2)

    threading.Thread(target=animate, daemon=True).start()
     
def destroy_player_zone(line, logger):
    global global_active_ship
    global global_active_ship_id
    if ("N/A" != global_active_ship) or ("N/A" != global_active_ship_id):
        logger.log(f"Ship Destroyed: {global_active_ship} with ID: {global_active_ship_id}")
        global_active_ship = "N/A"
        global_active_ship_id = "N/A"

def set_ac_ship(line, logger):
    global global_active_ship
    global_active_ship = line.split(' ')[5][1:-1]
    logger.log("Player has entered ship: ", global_active_ship)

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
    
    if global_game_mode == "EA_FreeFlight":
        if "Crash" in line:
            logger.log("Probably a ship reset, ignoring kill!")
            return False
        if "SelfDestruct" in line:
            logger.log("Self-destruct detected in EA_FreeFlight, ignoring kill!")
            return False

    elif global_game_mode == "EA_SquadronBattle":
        # Add your specific conditions for Squadron Battle mode
        if "Crash" in line:
            logger.log("Crash detected in EA_SquadronBattle, ignoring kill!")
            return False
        if "SelfDestruct" in line:
            logger.log("Self-destruct detected in EA_SquadronBattle, ignoring kill!")
            return False

    return True

def validate_api_key(api_key, player_name):
    url = "http://drawmyoshi.com:25966/validateKey"
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

def get_player_name(log_file_location, logger):
    global global_rsi_handle  # Use the global variable here
    # Retrieve the RSI handle using the existing function
    rsi_handle = find_rsi_handle(log_file_location)
    global_rsi_handle = find_rsi_handle(log_file_location)
    if not rsi_handle:
        logger.log("Error: RSI handle not found.")
        return None
    return rsi_handle

# Trigger kill event
def parse_kill_line(line, target_name, logger):
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
        logger.log("You have fallen in the service of BlightVeil.")

        # Send death-event to the server via heartbeat
        post_heartbeat_death_event(target_name, killed_zone, logger)
        destroy_player_zone(line, logger)
        return
    
    # Log a custom message for a successful kill
    event_message = f"You have killed {killed},"
    logger.log(event_message)

    json_data = {
        'player': target_name,
        'victim': killed,
        'time': kill_time,
        'zone': killed_zone,
        'weapon': weapon,
        'rsi_profile': rsi_profile,
        'game_mode': global_game_mode,
        'client_ver': "7.0",
        'killers_ship': global_active_ship,
        'anonymize_state': anonymize_state
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
            "http://drawmyoshi.com:25966/reportKill",
            headers=headers,
            data=json.dumps(json_data),
            timeout=30
        )
        if response.status_code == 200:
            play_random_sound()
            logger.log("and brought glory to the Veil.")
        else:
            logger.log(f"Servitor connectivity error: {response.status_code}.")
            logger.log("Relaunch BV Kill Tracker and reconnect with a new Key.")
    except requests.exceptions.RequestException as e:
        async_loading_animation(logger, app)
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
    global is_playing_sound
    app = tk.Tk()
    app.title("BlightVeil Kill Tracker V1.3")
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
        
        def activate_and_load_key():
            entered_key = key_entry.get().strip()  # Access key_entry here
            if not entered_key:
                # If the text box is empty, load the existing key
                try:
                    with open("killtracker_key.cfg", "r") as f:
                        entered_key = f.readline().strip()
                        if entered_key:
                            api_key["value"] = entered_key  # Assign the loaded key
                            logger.log(f"Existing key loaded: {entered_key}. Attempting to establish Servitor connection...")
                            if validate_api_key(entered_key, get_player_name(set_sc_log_location(), logger)):  # Pass logger here
                                logger.log("Servitor connection established.")
                                logger.log("Go Forth And Slaughter")
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
            else:
                # If the text box is not empty, proceed with activation
                log_file_location = set_sc_log_location()  # Assuming this is defined elsewhere
                if log_file_location:
                    player_name = get_player_name(log_file_location, logger)  # Pass logger here
                    if player_name:
                        if validate_api_key(entered_key, player_name):  # Pass both the key and player name
                            save_api_key(entered_key)  # Save the key for future use
                            logger.log("Key activated and saved. Servitor connection established.")
                            logger.log("Go Forth And Slaughter")
                            api_status_label.config(text="API Status: Valid (Expires in 72 hours)", fg="green")
                            start_api_key_countdown(entered_key, api_status_label)
                        else:
                            logger.log("Invalid key or player name. Please enter a valid API key.")
                            api_status_label.config(text="API Status: Invalid", fg="red")
                    else:
                        logger.log("RSI Handle not found. Please ensure the game is running and the log file is accessible.")
                        api_status_label.config(text="API Status: Error", fg="yellow")
                else:
                    logger.log("Log file location not found.")
                    api_status_label.config(text="API Status: Error", fg="yellow")

        # Update the button to use the new combined function
        activate_load_key_button = tk.Button(
            key_frame,
            text="Activate & Load Key",
            font=("Times New Roman", 12),
            command=activate_and_load_key,
            bg="#000000",
            fg="#ffffff",
        )
        activate_load_key_button.pack(side=tk.LEFT, padx=(5, 0))
        
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
        
        # Log Display
        text_area = scrolledtext.ScrolledText(
            app, wrap=tk.WORD, width=80, height=20, state=tk.DISABLED, bg="#282a36", fg="#f8f8f2", font=("Consolas", 12)
        )
        text_area.pack(padx=10, pady=10)

        logger = EventLogger(text_area)
        
        # Define the function to toggle the state
        def toggle_anonymize():
            if anonymize_state["enabled"]:
                anonymize_state["enabled"] = False
                anonymize_button.config(text="Enable Anonymity - Not Anonymous")
            else:
                anonymize_state["enabled"] = True
                anonymize_button.config(text="Disable Anonymity - Anonymous")
            logger.log(f"Anonymize state changed: {anonymize_state['enabled']}")

        # Add the button to the GUI
        anonymize_button = tk.Button(
            key_frame,
            text="Enable Anonymity - Not Anonymous",
            font=("Times New Roman", 12),
            command=toggle_anonymize,
            bg="#000000",
            fg="#ffffff",
        )
        anonymize_button.pack(side=tk.LEFT, padx=(5, 0))
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
        text="BlightVeil Kill Tracker - Credits: CyberBully-Actual, BossGamer09, Holiday, Samurai",
        font=("Times New Roman", 10),
        fg="#bcbcd8",
        bg="#3e3b4d",
    )
    footer_text.pack(pady=5)

    return app, logger

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
    
    start_hearbeat_button = tk.Button(
        commander_window,
        text="Connect to Commander",
        font=("Times New Roman", 12),
        command=lambda: start_heartbeat_thread(logger),  # Pass logger here
        bg="#000000",
        fg="#ffffff",
    )
    start_hearbeat_button.pack(pady=(10, 10))

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

    def check_for_updates():
        """
        Checks the update_queue for new commander data and refreshes the user list.
        This method should be called periodically from the Tkinter main loop.
        """
        if not update_queue.empty():
            active_commanders = update_queue.get()
            logger.refresh_user_list(active_commanders)

        # Check again after a short delay
        commander_window.after(1000, check_for_updates)  # Run every second

    # Assuming commander_window is your Tkinter window object
    commander_window.after(1000, check_for_updates)

    def clear_listboxes():
        """Cleanup listboxes when disconnected."""
        logger.connected_users.clear()
        logger.alloc_users.clear()
        connected_users_listbox.delete(0, tk.END)
        allocated_forces_listbox.delete(0, tk.END)

def post_heartbeat_death_event(target_name, killed_zone, logger):
    """Currently only support death events from the player!"""
    json_data = {
        'is_heartbeat': True,
        'player': target_name,
        'zone': killed_zone,
        'client_ver': "7.0",
        'status': "dead",  # Report status as 'dead'
        'mode': "commander"
    }

    headers = {
        'content-type': 'application/json',
        'Authorization': api_key["value"] if api_key["value"] else ""
    }

    try:
        response = requests.post(
            "http://drawmyoshi.com:25966/validateKey",
            headers=headers,
            data=json.dumps(json_data),
            timeout=5
        )
        if response.status_code != 200:
            logger.log(f"Failed to report death event: {response.status_code}.")
    except Exception as e:
        logger.log(f"Error reporting death event: {e}")

def post_heartbeat_enter_ship_event(rsi_handle, player_ship, logger):
    """Update the ship and set player to alive with heartbeat!"""
    json_data = {
        'is_heartbeat': True,
        'player': rsi_handle,
        'zone': player_ship,
        'client_ver': "7.0",
        'status': "alive",  # Report status as 'alive'
        'mode': "commander"
    }

    headers = {
        'content-type': 'application/json',
        'Authorization': api_key["value"] if api_key["value"] else ""
    }

    try:
        response = requests.post(
            "http://drawmyoshi.com:25966/validateKey",
            headers=headers,
            data=json.dumps(json_data),
            timeout=5
        )
        if response.status_code != 200:
            logger.log(f"Failed to report ship status event: {response.status_code}.")
    except Exception as e:
        logger.log(f"Error reporting ship status event: {e}")

def post_heartbeat(rsi_handle, logger):
    """
    Sends a heartbeat to the server every 5 seconds and updates the UI with active commanders.
    """
    global global_heartbeat_active
    global global_active_ship

    heartbeat_url = "http://drawmyoshi.com:25966/validateKey"
    headers = {
        'content-type': 'application/json',
        'Authorization': api_key["value"] if api_key["value"] else ""
    }
    global_heartbeat_active = True

    while global_heartbeat_active:
        time.sleep(5)

        # Determine status based on the active ship
        status = "alive" if global_active_ship != "N/A" else "dead"

        json_data = {
            'is_heartbeat': True,
            'player': rsi_handle,
            'zone': global_active_ship,
            'client_ver': "7.0",
            'status': status,
            'mode': "commander"
        }

        if not api_key["value"]:
            logger.log("Heartbeat will not be sent. Enter valid key to establish connection with Servitor...")
            global_heartbeat_active = False
            return

        try:
            # logger.log(f"Sending heartbeat: {json_data}")
            response = requests.post(heartbeat_url, headers=headers, json=json_data, timeout=5)
            response.raise_for_status()  # Raises an exception for HTTP errors

            response_data = response.json()
            # logger.log(f"Received response: {response_data}")

            # Update the UI with active commanders if the response contains the key
            if 'commanders' in response_data:
                active_commanders = response_data['commanders']
                # Put the updated commanders list in the queue for the GUI thread to process
                update_queue.put(active_commanders)
            else:
                logger.log("No commanders found in response.")

        except requests.RequestException as e:
            logger.log(f"Error sending heartbeat: {e}")
            global_heartbeat_active = False
            return        

def start_heartbeat_thread(logger):
    """Start the heartbeat in a seperate thread"""
    global global_rsi_handle
    global global_heartbeat_active
    global global_heartbeat_daemon
    if global_heartbeat_active:
        logger.log("Already connected to commander!")
        return
    logger.log("Connecting to commander...")
    global_heartbeat_daemon = threading.Thread(target=post_heartbeat, args=(global_rsi_handle, logger))
    global_heartbeat_daemon.daemon = True
    global_heartbeat_daemon.start()

def stop_heartbeat_thread(logger):
    global global_heartbeat_active
    global global_heartbeat_daemon
    if global_heartbeat_active:
        logger.log("Flagging heartbeat to shut down")
        global_heartbeat_active = False
        global_heartbeat_daemon.join()
        return

#API Key Management
def run_api_key_expiration_check(api_key):
    """Run get_api_key_expiration_time in a separate thread."""
    thread = threading.Thread(target=get_api_key_expiration_time, args=(api_key,))
    thread.daemon = True  # Ensures the thread exits when the program closes
    thread.start()

def start_api_key_countdown(api_key, api_status_label):
    """
    Function to start the countdown for the API key's expiration, refreshing expiry data periodically.
    """
    def fetch_expiration_time():
        """Fetch expiration time in a separate thread and update countdown."""
        def threaded_request():
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

            # Refresh expiration time every 60 seconds in a new thread
            api_status_label.after(60000, fetch_expiration_time)

        thread = threading.Thread(target=threaded_request)
        thread.daemon = True
        thread.start()

    fetch_expiration_time()  # Initial call

def get_api_key_expiration_time(api_key):
    """
    Retrieve the expiration time for the API key from the validation server.
    """
    url = "http://drawmyoshi.com:25966/validateKey"
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
        
def tail_log(log_file_location, rsi_name, logger):
    """Read the log file and display events in the GUI."""
    global global_game_mode, global_player_geid
    sc_log = open(log_file_location, "r")
    if sc_log is None:
        logger.log(f"No log file found at {log_file_location}.")
        return
    logger.log("Kill Tracking Initiated...")
    copy_new_sounds()
    copy_sounds_to_target_folder()
    logger.log(f"Looking for sounds in: {SOUNDS_FOLDER}")
    logger.log(f"Files inside: {os.listdir(SOUNDS_FOLDER) if os.path.exists(SOUNDS_FOLDER) else 'Not Found'}")
    logger.log("To Add new Sounds Drag .wav files to the sounds folder and restart either Star Citizen Or KT")
    logger.log("Enter key to establish Servitor connection...")

    # Read all lines to find out what game mode player is currently, in case they booted up late.
    # Don't upload kills, we don't want repeating last sessions kills incase they are actually available.
    lines = sc_log.readlines()
    logger.log("Loading old log (if available)! Kills shown will not be uploaded as they are stale.")
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
    """ Start the log tailing in a separate thread only if it's not already running. """
    if not logger.is_monitoring:  # Make sure the tailing isn't already started
        thread = threading.Thread(target=tail_log, args=(log_file_location, rsi_name, logger))
        thread.daemon = True
        thread.start()
        logger.is_monitoring = True

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
    try:
        game_running = is_game_running()

        app, logger = setup_gui(game_running)

        if game_running:
            # Start log monitoring in a separate thread
            log_file_location = set_sc_log_location()
            if log_file_location:
                rsi_handle = find_rsi_handle(log_file_location)
                if rsi_handle:
                    start_tail_log_thread(log_file_location, rsi_handle, logger)

                # Start monitoring game state in a separate thread
                if rsi_handle:  # Ensure rsi_handle is valid
                    game_state_thread = threading.Thread(target=monitor_game_state, args=(log_file_location, rsi_handle, logger))
                    game_state_thread.daemon = True
                    game_state_thread.start()

        # Initiate auto-shutdown after 72 hours
        if logger:
            auto_shutdown(app, 72 * 60 * 60, logger)  
        else:
            auto_shutdown(app, 72 * 60 * 60)

        app.mainloop()

    except KeyboardInterrupt:
        print("Program interrupted. Exiting gracefully...")
        # Optionally add any cleanup or logging here before exiting.

    except Exception as e:
        print(f"Unexpected error: {e}")
        # Optionally log the error