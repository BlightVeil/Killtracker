import os
import json
import psutil
import requests
import threading
import logging
logger = logging.getLogger("BlightVeilKillTracker")
import webbrowser
import tkinter as tk
from tkinter import scrolledtext
from tkinter.font import Font
from tkinter import messagebox
import sys
from packaging import version
import time

local_version = "1.0"
api_key = {"value": None}

is_authenticated = False  # Flag to track authentication state
heartbeat_initialized = False
auth_logged_in = False

global_game_mode = "Nothing"
global_active_ship = "N/A"
global_active_ship_id = "N/A"
global_player_geid = "N/A"
global_heartbeat_active = False
global_rsi_handle = ""

debug_mode = False
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

global_ship_list = [
    'DRAK', 'ORIG', 'AEGS', 'ANVL', 'CRUS', 'BANU', 'MISC',
    'KRIG', 'XNAA', 'ARGO', 'VNCL', 'ESPR', 'RSI', 'CNOU',
    'GRIN', 'TMBL', 'GAMA'
]

# Function to toggle debug mode
def toggle_debug_mode(enable_debug):
    global debug_mode
    debug_mode = enable_debug

class EventLogger:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def log(self, message):
        self._write_message(message)

    def error(self, message):
        self._write_message(f"ERROR: {message}")

    def warning(self, message):
        self._write_message(f"WARNING: {message}")
    
    def info(self, message):
        self._write_message(f"INFO: {message}")

    def debug(self, message):
        """Log debug messages only when debug mode is enabled."""
        if debug_mode:  # Only log if debug_mode is True
            self._write_message(f"DEBUG: {message}")

    def _write_message(self, message):
        """Insert the message into the text widget for display."""
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, message + "\n")
        self.text_widget.config(state=tk.DISABLED)
        self.text_widget.see(tk.END)

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
        logger.debug(f"Sending request to GitHub API: {github_api_url}")  # Debug log for the request

        response = requests.get(github_api_url, headers=headers, timeout=5)

        if response.status_code == 200:
            release_data = response.json()
            remote_version = release_data.get("tag_name", "v1.0").strip("v")
            download_url = release_data.get("html_url", "")

            # Logging versions for debugging
            logger.info(f"Local Version: {local_version}, Remote Version: {remote_version}")

            if version.parse(local_version) < version.parse(remote_version):
                update_message = f"Update available: {remote_version}. Download it here: {download_url}"
                logger.info(update_message)
                return update_message
            else:
                logger.debug(f"No update available. Current version is up to date.")  # Debug log for no update
        else:
            logger.error(f"GitHub API error: {response.status_code}")
    except Exception as e:
        logger.error(f"Error checking for updates: {e}")
    return None

def show_loading_animation(logger, app):
    logger.debug("Starting loading animation...")  # Debug log when the animation starts

    for dots in [".","..", "..."]:
        logger.log(dots)  # Log each dot set
        logger.debug(f"Animating: {dots}")  # Debug log for each animation step
        app.update_idletasks()  # Ensure the UI stays responsive
        time.sleep(0.2)  # Sleep briefly before updating the animation

    logger.debug("Loading animation completed.")  # Debug log when the animation ends

def destroy_player_zone(line, logger):
    global global_active_ship
    global global_active_ship_id

    # Debug log before the condition to check current values
    logger.debug(f"Checking if the active ship should be destroyed: Ship = {global_active_ship}, Ship ID = {global_active_ship_id}")

    if ("N/A" != global_active_ship) or ("N/A" != global_active_ship_id):
        logger.log(f"Ship Destroyed: {global_active_ship} with ID: {global_active_ship_id}")
        
        # Debug log when the active ship is being reset
        logger.debug(f"Resetting active ship and ID to 'N/A'. Previous Ship: {global_active_ship}, Previous Ship ID: {global_active_ship_id}")

        global_active_ship = "N/A"
        global_active_ship_id = "N/A"
        
        # Debug log after resetting
        logger.debug(f"Active ship and ID reset successfully. New Ship: {global_active_ship}, New Ship ID: {global_active_ship_id}")

def set_ac_ship(line, logger):
    global global_active_ship
    
    # Debug log before extracting the ship name
    logger.debug(f"Received line for set_ac_ship: {line}")

    global_active_ship = line.split(' ')[5][1:-1]
    
    # Log the ship name after extracting it
    logger.log(f"Player has entered ship: {global_active_ship}")

    # Debug log after updating the global variable
    logger.debug(f"Updated global_active_ship to: {global_active_ship}")

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

    # Debug log: show the data being sent
    logger.debug(f"Sending heartbeat with data: {json_data}")

    try:
        response = requests.post(
            "http://38.46.216.78:25966/validateKey",
            headers=headers,
            data=json.dumps(json_data),
            timeout=5
        )
        
        # Debug log: show the status code and response content for debugging
        logger.debug(f"Response Status Code: {response.status_code}")
        logger.debug(f"Response Body: {response.text}")

        if response.status_code != 200:
            logger.error(f"Failed to report ship status event: {response.status_code}.")
        else:
            logger.log(f"Successfully reported ship status event for player: {rsi_handle}")
    except Exception as e:
        logger.error(f"Error reporting ship status event: {e}")

def set_player_zone(line, logger, active_zone_label):
    global global_active_ship
    global global_active_ship_id
    global global_heartbeat_active
    global global_rsi_handle

    # Find where the zone information starts in the line
    line_index = line.index("-> Entity ") + len("-> Entity ")
    if 0 == line_index:
        # Log if there's no valid zone information
        logger.debug(f"Active Zone Change: {global_active_ship}")
        global_active_ship = "N/A"
        active_zone_label.config(text=f"Active Zone: {global_active_ship}")  # Update the label
        return

    # Extract the potential zone from the line
    potential_zone = line[line_index:].split(' ')[0]
    potential_zone = potential_zone[1:-1]  # Remove leading/trailing characters

    logger.debug(f"Potential Zone Extracted: {potential_zone}")

    # Check if the potential zone matches any entries in the global ship list
    for x in global_ship_list:
        if potential_zone.startswith(x):
            global_active_ship = potential_zone[:potential_zone.rindex('_')]
            global_active_ship_id = potential_zone[potential_zone.rindex('_') + 1:]

            # Log the successful zone change
            logger.debug(f"Active Zone Change: {global_active_ship} with ID: {global_active_ship_id}")

            # If heartbeat is active, send the heartbeat event
            if global_heartbeat_active:
                logger.debug(f"Sending heartbeat for {global_rsi_handle} in zone {global_active_ship}")
                post_heartbeat_enter_ship_event(global_rsi_handle, global_active_ship, logger)

            # Update the active zone label
            active_zone_label.config(text=f"Active Zone: {global_active_ship}")  # Update the label
            return
    # If no match is found, log that no update occurred
    logger.debug(f"No match found for zone in global_ship_list: {potential_zone}")

def check_if_process_running(process_name):
    """ Check if a process is running by name. """
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        if process_name.lower() in proc.info['name'].lower():
            return proc.info['exe']
    return None

def find_game_log_in_directory(directory, logger):
    """ Search for Game.log in the directory and its parent directory. """
    
    logger.debug(f"Searching for Game.log in directory: {directory}")

    # Check for the Game.log in the current directory
    game_log_path = os.path.join(directory, 'Game.log')
    if os.path.exists(game_log_path):
        logger.info(f"Found Game.log in: {directory}")
        return game_log_path

    # If not found in the current directory, check the parent directory
    parent_directory = os.path.dirname(directory)
    logger.debug(f"Game.log not found in {directory}, checking parent directory: {parent_directory}")
    
    game_log_path = os.path.join(parent_directory, 'Game.log')
    if os.path.exists(game_log_path):
        logger.info(f"Found Game.log in parent directory: {parent_directory}")
        return game_log_path
    
    # If still not found, log a warning
    logger.warning("Game.log not found in the directory or parent directory.")
    return None

def set_sc_log_location(logger):
    """ Check for RSI Launcher and Star Citizen Launcher, and set SC_LOG_LOCATION accordingly. """
    
    # Check if RSI Launcher is running
    rsi_launcher_path = check_if_process_running("RSI Launcher")
    if not rsi_launcher_path:
        logger.warning("RSI Launcher not running.")
        return None

    logger.debug(f"RSI Launcher running at: {rsi_launcher_path}")

    # Check if Star Citizen Launcher is running
    sc_launcher_path = check_if_process_running("StarCitizen")
    if not sc_launcher_path:
        logger.warning("Star Citizen Launcher not running.")
        return None

    logger.debug(f"Star Citizen Launcher running at: {sc_launcher_path}")

    # Search for Game.log in the folder next to StarCitizen_Launcher.exe
    star_citizen_dir = os.path.dirname(sc_launcher_path)
    logger.debug(f"Star Citizen directory located at: {star_citizen_dir}")
    
    logger.debug(f"Searching for Game.log in directory: {star_citizen_dir}")
    log_path = find_game_log_in_directory(star_citizen_dir, logger)

    if log_path:
        logger.debug(f"Found Game.log at: {log_path}")
        logger.debug(f"Setting SC_LOG_LOCATION to: {log_path}")
        os.environ['SC_LOG_LOCATION'] = log_path
        return log_path
    else:
        logger.warning("Game.log not found in expected locations.")
        return None
            
# Substrings to ignore
ignore_kill_substrings = [
    'PU_Pilots',
    'NPC_Archetypes',
    'PU_Human',
    'kopion',
    'marok',
]

def check_substring_list(line, substring_list, logger):
    """
    Check if any substring from the list is present in the given line.
    """
    for substring in substring_list:
        if substring.lower() in line.lower():
            logger.info(f"Found substring '{substring}' in line.")
            return True
    return False

def check_exclusion_scenarios(line, logger):
    global global_game_mode
    
    logger.debug(f"Checking exclusion scenarios. Current game mode: {global_game_mode}, Line content: {line}")

    if global_game_mode == "EA_FreeFlight" and -1 != line.find("Crash"):
        logger.info("Probably a ship reset, ignoring kill!")
        return False
    
    logger.debug("Exclusion check passed.")
    return True

def start_heartbeat(logger, status_label):
    global heartbeat_initialized  # Ensure we modify the global variable

    def send_heartbeat():
        global heartbeat_initialized  # Make sure to access the global variable inside the thread

        while True:
            try:
                if global_rsi_handle:
                    # Only log the heartbeat once
                    if not heartbeat_initialized:
                        logger.debug("Heartbeat initiated...")  # Debugging the initialization of the heartbeat
                        heartbeat_initialized = True  # Set the global variable here
                        status_label.config(text="Heartbeat: Connected", bg="green")  # Update connection window

                    # Send heartbeat request to server
                    logger.debug(f"Sending heartbeat for player {global_rsi_handle} in zone {global_active_ship}...")
                    heartbeat_url = "http://38.46.216.78:25966/validateKey"
                    headers = {
                        'Content-Type': 'application/json',
                        "Authorization": api_key["value"],  # Use saved API key
                    }
                    payload = {
                        "player": global_rsi_handle,  # Player (RSI handle)
                        "zone": global_active_ship,  # Zone of the player
                        "status": "alive"  # Player status
                    }

                    response = requests.post(heartbeat_url, headers=headers, json=payload, timeout=30)
                    if response.status_code == 200:
                        # Only update the window if necessary
                        active_users = response.json().get('active_users', [])
                        if active_users:
                            logger.debug(f"Heartbeat successful. {len(active_users)} active users.")
                            status_label.config(text=f"Heartbeat: Connected - {len(active_users)} users active", bg="green")
                    else:
                        logger.error(f"Failed to send heartbeat. Status code: {response.status_code}")
                        status_label.config(text="Heartbeat: Connection lost", bg="red")

            except Exception as e:
                logger.error(f"Error sending heartbeat: {e}")
                status_label.config(text="Heartbeat: Connection lost", bg="red")
            
            time.sleep(10)  # Wait for 10 seconds before sending the next heartbeat

    heartbeat_thread = threading.Thread(target=send_heartbeat)
    heartbeat_thread.daemon = True  # Allow the thread to exit when the main program exits
    heartbeat_thread.start()

def post_heartbeat_death_event(target_name, killed_zone, logger):
    """Currently only supports death events from the player!"""
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
        logger.debug(f"Preparing to report death event for player: {target_name} in zone: {killed_zone}...")
        response = requests.post(
            "http://38.46.216.78:25966/validateKey",
            headers=headers,
            data=json.dumps(json_data),
            timeout=5
        )
        if response.status_code != 200:
            logger.error(f"Failed to report death event: {response.status_code}.")
        else:
            logger.info(f"Successfully reported death event for player: {target_name} in zone: {killed_zone}")
    except Exception as e:
        logger.error(f"Error reporting death event: {e}")

def post_kill_event(json_data, logger):
    """Send the kill event data to the server."""
    headers = {
        'content-type': 'application/json',
        'Authorization': api_key["value"] if api_key["value"] else ""
    }

    # Check if API key is available before attempting to send the event
    if not api_key["value"]:
        logger.warning("Kill event will not be sent. Enter a valid key to establish connection with Servitor...")
        return

    try:
        logger.debug(f"Preparing to send kill event: {json_data}")  # Log the event data being sent
        response = requests.post(
            "http://38.46.216.78:25966/reportKill",
            headers=headers,
            data=json.dumps(json_data)
        )
        if response.status_code == 200:
            logger.info("Kill event reported successfully and brought glory to the Veil.")
        else:
            logger.error(f"Servitor connectivity error: {response.status_code}.")
            logger.warning("Relaunch BV Kill Tracker and reconnect with a new Key.")
    except Exception as e:
        show_loading_animation(logger, app)  # Show the loading animation if there's an issue
        logger.error(f"Kill event will not be sent. Error: {e}")  # Log the error message
        logger.warning("Enter a valid key to establish connection with Servitor...")

def parse_kill_line(line, target_name, logger):
    """
    Parses a kill line from the log and handles player kills, deaths, and related events.
    """
    global global_active_ship
    global player_status  # Add a global status variable to track player's state
    player_status = "alive"  # Default status is alive

    # Check exclusion scenarios (e.g., reset cases or non-relevant kills)
    if not check_exclusion_scenarios(line, logger):
        return

    # Split the log line into parts for easier handling
    split_line = line.split(' ')

    # Extract relevant information from the log line
    kill_time = split_line[0].strip('\'')
    killed = split_line[5].strip('\'')
    killed_zone = split_line[9].strip('\'')
    killer = split_line[12].strip('\'')
    weapon = split_line[15].strip('\'')
    rsi_profile = f"https://robertsspaceindustries.com/citizens/{killed}"

    logger.debug(f"Parsed Kill Line: Time={kill_time}, Killed={killed}, Zone={killed_zone}, Killer={killer}, Weapon={weapon}")

    # Handle the case where the player is the victim of a kill
    if killed == killer or killer.lower() == "unknown" or killed == target_name:
        # Log the death event for the player
        show_loading_animation(logger, app)
        logger.info("You have fallen in the service of BlightVeil.")

        # Send death-event to the server via heartbeat
        post_heartbeat_death_event(target_name, killed_zone, logger)

        # Destroy the player's zone after death
        destroy_player_zone(line, logger)
        return

    # If the player is not the victim, it means they are the killer
    logger.debug(f"Player {target_name} has killed {killed}. Weapon: {weapon}")

    # Log a custom message for a successful kill
    show_loading_animation(logger, app)
    event_message = f"You have killed {killed} in zone {killed_zone} with {weapon}."
    logger.info(event_message)

    # Prepare the data for the Discord bot (or other reporting service)
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
    logger.debug(f"Sending kill event data: {json_data}")

    # Send the kill event data to the server
    post_kill_event(json_data, logger)

def read_existing_log(log_file_location, rsi_handle, logger):
    sc_log = open(log_file_location, "r")
    lines = sc_log.readlines()
    for line in lines:
        read_log_line(line, rsi_handle, True, logger)

def find_rsi_handle(log_file_location, logger):
    acct_str = "<Legacy login response> [CIG-net] User Login Success"
    
    try:
        with open(log_file_location, "r") as sc_log:
            lines = sc_log.readlines()
            for line in lines:
                if acct_str in line:
                    try:
                        line_index = line.index("Handle[") + len("Handle[")
                        if line_index == len("Handle["):
                            logger.error("RSI_HANDLE: Not Found in the line!")
                            return None  # Return None instead of exiting
                        
                        potential_handle = line[line_index:].split(' ')[0].strip()[:-1]  # Stripping any excess whitespace
                        logger.info(f"Found RSI_HANDLE: {potential_handle}")
                        return potential_handle
                    except ValueError as e:
                        logger.error(f"Error parsing handle from line: {line}. Error: {e}")
                        return None
    except FileNotFoundError:
        logger.error(f"Log file not found at: {log_file_location}")
    except Exception as e:
        logger.error(f"Error reading the log file: {e}")
    
    return None

def find_rsi_geid(log_file_location, logger):
    global global_player_geid
    acct_kw = "AccountLoginCharacterStatus_Character"
    
    try:
        with open(log_file_location, "r") as sc_log:
            lines = sc_log.readlines()
            for line in lines:
                if acct_kw in line:
                    try:
                        # Split line and check for correct index to avoid index errors
                        split_line = line.split(' ')
                        if len(split_line) > 11:
                            global_player_geid = split_line[11]
                            logger.info(f"Player geid found: {global_player_geid}")
                            return
                        else:
                            logger.error(f"Unexpected line format: {line}")
                            return
                    except IndexError as e:
                        logger.error(f"Error extracting geid from line: {line}. Error: {e}")
                        return
    except FileNotFoundError:
        logger.error(f"Log file not found at: {log_file_location}")
    except Exception as e:
        logger.error(f"Error reading the log file: {e}")

def set_game_mode(line, logger):
    global global_game_mode
    global global_active_ship
    global global_active_ship_id
    try:
        split_line = line.split(' ')
        game_mode = split_line[8].split("=")[1].strip("\"")
        
        if game_mode != global_game_mode:
            logger.info(f"Game mode changed from {global_game_mode} to {game_mode}")
            global_game_mode = game_mode

        if "SC_Default" == global_game_mode:
            if global_active_ship != "N/A":
                logger.info(f"Resetting active ship from {global_active_ship} to N/A due to SC_Default game mode.")
            global_active_ship = "N/A"
            global_active_ship_id = "N/A"
            logger.info("Active ship reset to N/A due to SC_Default game mode.")

    except IndexError:
        logger.error(f"Error processing game mode from line: {line}")
    except Exception as e:
        logger.error(f"Unexpected error in set_game_mode: {e}")

def load_existing_key(app, logger, status_label):
    try:
        f = open("killtracker_key.cfg", "r")
        entered_key = f.readline()

        if entered_key:
            logger.info("Activating key")
            show_loading_animation(logger, app)
            logger.info("Initiating Servitor Connection")
            show_loading_animation(logger, app)

            heartbeat_url = "http://38.46.216.78:25966/validateKey"
            headers = {
                'Content-Type': 'application/json',
                "Authorization": entered_key  # API key is set in Authorization header
            }

            # Ensure that global_rsi_handle is available and correct
            if not global_rsi_handle:
                logger.error("RSI handle is missing. Cannot proceed with activation.")
                status_label.config(text="RSI handle not found", bg="red")
                return

            # Prepare the payload including the RSI handle (player) and API key
            payload = {
                "player": global_rsi_handle,  # Use the global RSI handle
                "zone": global_active_ship,
                "status": "alive",  # Default status if not provided
            }

            logger.debug(f"Sending Authorization header: {entered_key}")
            logger.debug(f"Payload: {payload}")

            try:
                response = requests.post(heartbeat_url, headers=headers, json=payload, timeout=30)
                logger.debug(f"Response Status Code: {response.status_code}")
                logger.debug(f"Response Body: {response.text}")

                if response.status_code == 200:
                    response_data = response.json()
                    if response_data.get("status") == "valid":
                        api_key["value"] = entered_key
                        logger.info("Servitor Connection Established.")
                        logger.info("Go forth and KILL...")
                        status_label.config(text="Connection Established", bg="green")

                        # Start the heartbeat process after successful authentication
                        start_heartbeat(logger, status_label)
                    else:
                        logger.warning("Invalid key. Please input a valid key to establish connection with Servitor.")
                        status_label.config(text="Invalid Key", bg="red")
                else:
                    logger.error(f"Servitor connectivity error NewKey: {response.status_code}.")
                    logger.debug(f"Response Body: {response.text}")  # More info for debugging
                    status_label.config(text="Connection Error", bg="red")
            except requests.exceptions.Timeout:
                logger.error("Connection timeout while trying to connect to the Servitor.")
                status_label.config(text="Connection Timeout", bg="red")
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e}")
                status_label.config(text="Connection Error", bg="red")

        else:
            logger.warning("Error: No key detected. Input a valid key to establish connection with Servitor.")
            status_label.config(text="Invalid Key", bg="red")

    except Exception as e:
        logger.error(f"Unexpected error in activate_key: {e}")
        status_label.config(text="Error Occurred", bg="red")

def activate_key(app, key_entry, logger, status_label):
    try:
        entered_key = key_entry.get().strip()
        if entered_key:
            logger.info("Activating key")
            show_loading_animation(logger, app)
            logger.info("Initiating Servitor Connection")
            show_loading_animation(logger, app)
            heartbeat_url = "http://38.46.216.78:25966/validateKey"
            headers = {
                'Content-Type': 'application/json',
                "Authorization": entered_key  # API key is set in Authorization header
            }

            # Ensure that global_rsi_handle is available and correct
            if not global_rsi_handle:
                logger.error("RSI handle is missing. Cannot proceed with activation.")
                status_label.config(text="RSI handle not found", bg="red")
                return

            # Prepare the payload including the RSI handle (player) and API key
            payload = {
                "player": global_rsi_handle,  # Use the global RSI handle
                "zone": global_active_ship,
                "status": "alive",  # Default status if not provided
            }

            logger.debug(f"Sending Authorization header: {entered_key}")
            logger.debug(f"Payload: {payload}")

            try:
                response = requests.post(heartbeat_url, headers=headers, json=payload, timeout=30)
                logger.debug(f"Response Status Code: {response.status_code}")
                logger.debug(f"Response Body: {response.text}")

                if response.status_code == 200:
                    response_data = response.json()
                    if response_data.get("status") == "valid":
                        api_key["value"] = entered_key
                        logger.info("Servitor Connection Established.")
                        logger.info("Go forth and KILL...")
                        status_label.config(text="Connection Established", bg="green")

                        # Start the heartbeat process after successful authentication
                        start_heartbeat(logger, status_label)
                    else:
                        logger.warning("Invalid key. Please input a valid key to establish connection with Servitor.")
                        status_label.config(text="Invalid Key", bg="red")
                else:
                    logger.error(f"Servitor connectivity error NewKey: {response.status_code}.")
                    logger.debug(f"Response Body: {response.text}")  # More info for debugging
                    status_label.config(text="Connection Error", bg="red")
            except requests.exceptions.Timeout:
                logger.error("Connection timeout while trying to connect to the Servitor.")
                status_label.config(text="Connection Timeout", bg="red")
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e}")
                status_label.config(text="Connection Error", bg="red")

            # Save the entered key to the config file
            with open("killtracker_key.cfg", "w") as f:
                f.write(entered_key)
            logger.info("API key saved successfully.")

        else:
            logger.warning("Error: No key detected. Input a valid key to establish connection with Servitor.")
            status_label.config(text="Invalid Key", bg="red")

    except Exception as e:
        logger.error(f"Unexpected error in activate_key: {e}")
        status_label.config(text="Error Occurred", bg="red")
        
def setup_game_running_gui(app):
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

    # Status Label
    status_label = tk.Label(
        app, text="Status: Not Connected", font=("Times New Roman", 12), fg="#ffffff", bg="gray", width=30
    )
    status_label.pack(pady=(10, 10))

    # Active Zone Label
    active_zone_label = tk.Label(
        app, text="Active Zone: N/A", font=("Times New Roman", 12), fg="#ffffff", bg="#484759", width=30
    )
    active_zone_label.pack(pady=(10, 10))

    # Activate Button
    activate_button = tk.Button(
        key_frame,
        text="Activate",
        font=("Times New Roman", 12),
        command=lambda: activate_key(app, key_entry, logger, status_label),
        bg="#000000",
        fg="#ffffff",
    )
    activate_button.pack(side=tk.LEFT, padx=(5, 0))

    # Load Key Button
    load_key_button = tk.Button(
        key_frame,
        text="Load Existing Key",
        font=("Times New Roman", 12),
        command=lambda: load_existing_key(app, logger, status_label),
        bg="#000000",
        fg="#ffffff",
    )
    load_key_button.pack(side=tk.LEFT, padx=(5, 0))

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

    logger.log("Game running GUI setup completed.")
    return logger, active_zone_label  # Return active_zone_label so it can be updated

# Initialize the logger
def setup_logger():
    logger = logging.getLogger("BlightVeilKillTracker")
    logger.setLevel(logging.DEBUG)
    # Set up the log file handler
    file_handler = logging.FileHandler("blightveil.log")
    file_handler.setLevel(logging.DEBUG)
    # Set up a console handler (optional)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    # Set the log format
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

def setup_gui(game_running):
    app = tk.Tk()
    app.title("BlightVeil Kill Tracker")
    app.geometry("800x800")
    app.configure(bg="#484759")

    # Initialize the logger
    logger = setup_logger()

    # Set the icon
    try:
        icon_path = resource_path("BlightVeil.ico")
        if os.path.exists(icon_path):
            app.iconbitmap(icon_path)
            logger.info(f"Icon loaded successfully from: {icon_path}")
        else:
            logger.warning(f"Icon not found at: {icon_path}")
    except Exception as e:
        logger.error(f"Error setting icon: {e}")

    # Add Banner
    try:
        banner_path = resource_path("BlightVeilBanner.png")
        banner_image = tk.PhotoImage(file=banner_path)
        banner_label = tk.Label(app, image=banner_image, bg="#484759")
        banner_label.image = banner_image  # Keep a reference to the image to avoid garbage collection
        banner_label.pack(pady=(0, 10))
        logger.info("Banner image loaded successfully.")
    except Exception as e:
        logger.error(f"Error loading banner image: {e}")

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
        logger.info(f"Update message: {update_message}")

        def open_github(event):
            try:
                url = update_message.split("Download it here: ")[-1]
                webbrowser.open(url)
                logger.info(f"Opening GitHub link: {url}")
            except Exception as e:
                logger.error(f"Error opening GitHub link: {e}")

        update_label.bind("<Button-1>", open_github)

    # Game Running or Not
    if game_running:
        logger.info("Game is running. Setting up the game running GUI.")
        setup_game_running_gui(app)
    else:
        message_label = tk.Label(
            app,
            text="You must launch Star Citizen before starting the tracker.\n\nPlease close this window, launch Star Citizen, and relaunch the BV Kill Tracker.",
            font=("Times New Roman", 14),
            fg="#000000",
            bg="#484759",
            wraplength=700,
            justify="center",
        )
        message_label.pack(pady=(50, 10))
        logger.warning("Game not running. Displaying message to the user.")
    # Footer
    footer = tk.Frame(app, bg="#3e3b4d")
    footer.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)  # Added padding

    footer_text = tk.Label(
        footer,
        text="BlightVeil Kill Tracker - Credits: CyberBully-Actual, BossGamer09, Holiday",
        font=("Times New Roman", 10),
        fg="#bcbcd8",
        bg="#3e3b4d",
    )
    footer_text.pack(pady=5)

    return app, logger  # Make sure this is the LAST return statement in the function

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
                # Remove from connected users list
                connected_users_listbox.delete(index)

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
    if (-1 != line.find("CActor::Kill:")):
        print(" break")
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
        logger.debug(f"Handle Mention: {line.strip()}")
        if -1 != line.find("OnEntityEnterZone"):
            active_zone_label = tk.Label(app, text="Active Zone: Unknown", font=("Consolas", 12))
            active_zone_label.pack(pady=10)
            set_player_zone(line, logger, active_zone_label,)
        if (-1 != line.find("CActor::Kill:")):
            parse_kill_line(line, rsi_handle, logger)

def tail_log(log_file_location, rsi_handle, logger):
    """Read the log file and display events in the GUI."""
    try:
        # Open the log file for reading
        sc_log = open(log_file_location, "r")
        logger.debug(f"Log file opened successfully: {log_file_location}")
    except FileNotFoundError:
        # If log file is not found, log an error message and exit
        logger.error(f"No log file found at {log_file_location}.")
        return
    
    logger.info("Kill Tracking Initiated...")
    logger.info("Enter key to establish Servitor connection...")

    # Read all lines initially to determine the current game mode and state, avoid uploading stale kills
    lines = sc_log.readlines()
    logger.debug("Old log loaded, starting to read existing entries.")
    logger.info("Loading old log (if available)! Kills shown will not be uploaded as they are stale.")
    
    for line in lines:
        read_log_line(line, rsi_handle, False, logger)

    # Main loop to monitor the log for new entries
    last_log_file_size = os.stat(log_file_location).st_size
    logger.debug(f"Initial log file size: {last_log_file_size} bytes.")
    logger.info("Beginning real-time log monitoring...")

    while True:
        try:
            where = sc_log.tell()
            line = sc_log.readline()

            if not line:
                # No new lines, so sleep for 1 second before checking again
                time.sleep(1)
                sc_log.seek(where)

                # Handle log rotation or file truncation
                current_log_file_size = os.stat(log_file_location).st_size
                if current_log_file_size < last_log_file_size:
                    logger.warning("Log file size decreased, reopening the file...")
                    sc_log.close()
                    sc_log = open(log_file_location, "r")
                    last_log_file_size = current_log_file_size
                    logger.debug(f"Log file reopened. New file size: {current_log_file_size} bytes.")
            else:
                # Process new log line and pass it to the relevant handler
                # logger.debug(f"New log line: {line.strip()}")
                read_log_line(line, rsi_handle, True, logger)

        except Exception as e:
            # Log any unexpected errors
            logger.error(f"Error reading log file: {e}")
            break

def start_tail_log_thread(log_file_location, rsi_handle, logger):
    """Start the log tailing in a separate thread."""
    thread = threading.Thread(target=tail_log, args=(log_file_location, rsi_handle, logger))
    thread.daemon = True
    thread.start()

def is_game_running():
    """Check if Star Citizen is running."""
    return check_if_process_running("StarCitizen") is not None

def auto_shutdown(app, delay_in_seconds, logger=None):
    """
    Automatically shuts down the application after a specified delay.
    
    :param app: The Tkinter application window instance
    :param delay_in_seconds: The delay before initiating shutdown (in seconds)
    :param logger: Optional logger for logging messages
    """
    def shutdown():
        try:
            # Wait for the specified delay time
            time.sleep(delay_in_seconds)
            # Log the shutdown message
            if logger:
                logger.log("Application has been open for 72 hours. Shutting down in 60 seconds.") 
            else:
                print("Application has been open for 72 hours. Shutting down in 60 seconds.")  
            # Wait for 60 more seconds before shutting down
            time.sleep(60)
            # Close the Tkinter app and exit the program
            app.quit() 
            sys.exit(0)  # Exit the program

        except Exception as e:
            # Handle any errors and log them
            if logger:
                logger.log(f"Error during shutdown: {e}")
            else:
                print(f"Error during shutdown: {e}")

    # Run the shutdown logic in a separate thread to prevent blocking the main GUI thread
    shutdown_thread = threading.Thread(target=shutdown, daemon=True)
    shutdown_thread.start()

if __name__ == '__main__':
    game_running = is_game_running()

    app, logger = setup_gui(game_running)

    if game_running:
        # Start log monitoring in a separate thread
        log_file_location = set_sc_log_location(logger)
        if log_file_location:
            rsi_handle = find_rsi_handle(log_file_location, logger)
            find_rsi_geid(log_file_location, logger)
            if rsi_handle:
                global_rsi_handle = rsi_handle
                start_tail_log_thread(log_file_location, rsi_handle, logger)
    
    # Initiate auto-shutdown after 72 hours (72 * 60 * 60 seconds)
    if logger:
        auto_shutdown(app, 72 * 60 * 60, logger)  # Pass logger only if initialized
    else:
        auto_shutdown(app, 72 * 60 * 60)  # Fallback without logger

    app.mainloop()
