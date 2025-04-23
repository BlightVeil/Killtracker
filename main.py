
from sys import exit
from psutil import process_iter
import time
import psutil
import shutil
import datetime
import warnings
warnings.filterwarnings("ignore", message="Couldn't find ffmpeg or avconv")
import threading
from queue import Queue

# Import kill tracker modules
from modules.api_client import API_Client
from modules.gui import GUI
from modules.log_parser import LogParser
from modules.sounds import Sounds
from modules.commander_mode.cm_api import CM_API_Client
from modules.commander_mode.cm_core import CM_Core
from modules.commander_mode.cm_gui import CM_GUI
import modules.helpers as Helpers

class KillTracker():
    """Official Kill Tracker for BlightVeil."""
    def __init__(self):
        self.local_version = "1.4"
        self.log = None
        self.log_parser = None
        #self.stop_event = threading.Event()
        self.is_monitoring = False
        self.anonymize_state = {"enabled": False}
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

    def monitor_game_state(self) -> None:
        """Continuously monitor the game state and manage log monitoring."""
        while True: # FIXME NEEDS BREAK CONDITION?
            try:
                game_running = self.is_game_running()

                if game_running and not self.is_monitoring:  # Log only when transitioning to running
                    self.log.success("Star Citizen is running. Starting log monitoring.")
                    #self.log.info("Ignore API Key if Status Is Green.")
                    self.log_parser.start_tail_log_thread()
                    self.is_monitoring = True

                elif not game_running and self.is_monitoring:  # Log only when transitioning to stopped
                    self.log.warning("Star Citizen has stopped. Pausing log monitoring...")
                    self.is_monitoring = False

                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                self.log.error(f"monitor_game_state(): Error: {e.__class__.__name__} {e}")

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
        gui_module = GUI(kt.local_version, kt.anonymize_state)
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

        if game_running:
            game_state_thread = threading.Thread(target=kt.monitor_game_state, args=())
            game_state_thread.daemon = True
            game_state_thread.start()

        # Initiate auto-shutdown after 72 hours
        if logger:
            auto_shutdown(app, 72 * 60 * 60, logger)  
        else:
            auto_shutdown(app, 72 * 60 * 60)

        check_for_cm_updates

        app.mainloop()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Program interrupted. Exiting gracefully...")
        # Optionally add any cleanup or logging here before exiting.
    except Exception as e:
        print(f"__main__: ERROR: {e.__class__.__name__} {e}")
