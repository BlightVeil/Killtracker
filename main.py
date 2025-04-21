from os import listdir, path
from sys import exit
from psutil import process_iter
import time
import psutil
import shutil
from pathlib import Path

import random
import winsound
import datetime
import warnings
warnings.filterwarnings("ignore", message="Couldn't find ffmpeg or avconv")
import threading
from queue import Queue

# Import kill tracker modules
from modules.api_client import API_Client
from modules.commander_mode.cm_core import CommanderMode
from modules.gui import GUI
from modules.log_parser import LogParser
from modules.sounds import Sounds
import modules.helpers as Helpers

class KillTracker():
    """Official KillTracker for BlightVeil."""
    def __init__(self):
        self.local_version = "1.4"
        self.log = None
        #self.stop_event = threading.Event()

        self.global_commander_heartbeat_status = False
        self.heartbeat_status = {"active": False}
        self.rsi_handle = {"current": "N/A"}
        self.active_ship = {"current": "N/A"}
        self.update_queue = Queue()
    
    def check_if_process_running(self, process_name):
        """Check if a process is running by name."""
        for proc in process_iter(['pid', 'name', 'exe']):
            if process_name.lower() in proc.info['name'].lower():
                return proc.info['exe']
        return None

    def is_game_running(self):
        """Check if Star Citizen is running."""
        return self.check_if_process_running("StarCitizen") is not None

    def monitor_game_state(self, log_file_location, rsi_name, logger) -> None:
        """Continuously monitor the game state and manage log monitoring."""
        while True: # FIXME NEEDS BREAK CONDITION?
            try:
                game_running = is_game_running()

                if game_running and not logger.is_monitoring:  # Log only when transitioning to running
                    logger.log("✅ Star Citizen is running. Starting log monitoring.")
                    #logger.log("Ignore API Key if Status Is Green")
                    start_tail_log_thread(log_file_location, rsi_name, logger)
                    logger.is_monitoring = True

                elif not game_running and logger.is_monitoring:  # Log only when transitioning to stopped
                    logger.log("⚠️ Star Citizen has stopped. Pausing log monitoring...")
                    logger.is_monitoring = False

                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                logger.log(f"❌ Error in monitor_game_state(): {e.__class__.__name__} {e}")


    def auto_shutdown(app, delay_in_seconds, logger=None):
        def shutdown():
            time.sleep(delay_in_seconds) 
            if logger:
                logger.log("Application has been open for 72 hours. Shutting down in 60 seconds.") 
            else:
                print("Application has been open for 72 hours. Shutting down in 60 seconds.")  

            time.sleep(60)

            app.quit() 
            exit(0) 

        # Run the shutdown logic in a separate thread
        shutdown_thread = threading.Thread(target=shutdown, daemon=True)
        shutdown_thread.start()

def main():
    try:
        kt = KillTracker()
    except Exception as e:
        print(f"main(): ERROR in creating the KillTracker instance: {e.__class__.__name__} {e}")

    try:
        game_running = kt.is_game_running()
    except Exception as e:
        print(f"main(): ERROR in checking if the game is running: {e.__class__.__name__} {e}")

    try:
        gui_module = GUI(kt.local_version)
        log = gui_module.log # Used to pass logger ref to other modules
    except Exception as e:
        print(f"main(): ERROR in setting up the GUI module: {e.__class__.__name__} {e}")

    try:
        api_client_module = API_Client(log, gui_module, kt.local_version, kt.heartbeat_status, kt.rsi_handle, kt.update_queue)
        gui_module.api = api_client_module
    except Exception as e:
        log.error(f"main(): ERROR in setting up the API Client module: {e.__class__.__name__} {e}")

    try:
        sound_module = Sounds(log)
    except Exception as e:
        log.error(f"main(): ERROR in setting up the Sounds module: {e.__class__.__name__} {e}")

    try:
        gui_module.setup_gui(game_running, kt.local_version)

              else:
                    self.log.log("⚠️ RSI Handle not found. Please ensure the game is running and the log file is accessible.")
                    api_status_label.config(text="API Status: Error", fg="yellow")
            else:
                self.log.log("⚠️ Log file location not found.")
                api_status_label.config(text="API Status: Error", fg="yellow")

        create_sounds_dir(logger)
        copy_success = copy_sounds(sounds_pyinst_dir, sounds_live_dir, logger)
        if copy_success:
            logger.log(f"Included sounds found at: {str(sounds_live_dir)}")
            logger.log(f"Sound Files inside: {listdir(str(sounds_live_dir)) if path.exists(str(sounds_live_dir)) else 'Not Found'}")
            logger.log("To add new Sounds to the Kill Tracker, copy .wav files to the sounds folder.")
        if game_running:
            # Start log monitoring in a separate thread
            log_file_location = get_sc_log_location(logger)

            if log_file_location:
                rsi_handle = find_rsi_handle(log_file_location)
                # Start monitoring game state in a separate thread
                if rsi_handle:  # Ensure RSI handle is valid
                    game_state_thread = threading.Thread(target=monitor_game_state, args=(log_file_location, rsi_handle, logger))
                    game_state_thread.daemon = True
                    game_state_thread.start()

        # Initiate auto-shutdown after 72 hours
        if logger:
            auto_shutdown(app, 72 * 60 * 60, logger)  
        else:
            auto_shutdown(app, 72 * 60 * 60)

        app.mainloop()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Program interrupted. Exiting gracefully...")
        # Optionally add any cleanup or logging here before exiting.
    except Exception as e:
        print(f"__main__: ERROR: {e.__class__.__name__} {e}")
