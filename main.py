
from sys import exit
from time import sleep
from os import path
from psutil import process_iter
from threading import Thread
from queue import Queue
import warnings
warnings.filterwarnings("ignore", message="Couldn't find ffmpeg or avconv")

# Import kill tracker modules
from modules.cfg_handler import Cfg_Handler
from modules.api_client import API_Client
from modules.gui import GUI
from modules.log_parser import LogParser
from modules.sounds import Sounds
from modules.commander_mode.cm_core import CM_Core

class KillTracker():
    """Official Kill Tracker for BlightVeil."""
    def __init__(self):
        self.local_version = "1.6"
        self.log = None
        self.log_parser = None
        self.cfg_module = None
        self.sounds_module = None
        self.monitoring = {"active": False}
        self.heartbeat_status = {"active": False}
        self.program_state = {"enabled": True}
        self.anonymize_state = {"enabled": False}
        self.mute_state = {"enabled": False}
        self.rsi_handle = {"current": "N/A"}
        self.player_geid = {"current": "N/A"}
        self.active_ship = {"current": "N/A", "previous": "N/A"}
        self.update_queue = Queue()    
        
    def check_if_process_running(self, process_name:str) -> str:
        """Check if a process is running by name."""
        try:
            for proc in process_iter(['name', 'exe']):
                if process_name.lower() == proc.info['name'].lower():
                    return proc.info['exe']
        except Exception as e:
            self.log.error(f"check_if_process_running(): {e.__class__.__name__} {e}")
        return ""
    
    def is_game_running(self) -> bool:
        """Check if Star Citizen is running."""
        try:
            if self.check_if_process_running("StarCitizen_Launcher.exe"):
                return True
            return False
        except Exception as e:
            self.log.error(f"is_game_running(): {e.__class__.__name__} {e}")
    
    def get_sc_processes(self) -> str:
        """Check for RSI Launcher and Star Citizen Launcher, and get the log path."""
        try:
            # Check if RSI Launcher is running
            rsi_launcher_path = self.check_if_process_running("RSI Launcher.exe")
            if not rsi_launcher_path:
                self.log.warning("RSI Launcher not running.")
                return ""
            self.log.debug(f"RSI Launcher running at: {rsi_launcher_path}")

            # Check if Star Citizen Launcher is running
            sc_launcher_path = self.check_if_process_running("StarCitizen_Launcher.exe")
            if not sc_launcher_path:
                self.log.warning("Star Citizen Launcher not running.")
                return ""
            self.log.debug(f"Star Citizen Launcher running at: {sc_launcher_path}")
            return sc_launcher_path
        except Exception as e:
            self.log.error(f"get_sc_processes(): {e.__class__.__name__} {e}")

    def get_sc_log_path(self, directory:str) -> str:
        """Search for Game.log in the directory and its parent directory."""
        try:
            game_log_path = path.join(directory, 'Game.log')
            if path.exists(game_log_path):
                self.log.debug(f"Found Game.log in: {directory}")
                return game_log_path
            # If not found in the same directory, check the parent directory
            parent_directory = path.dirname(directory)
            game_log_path = path.join(parent_directory, 'Game.log')
            if path.exists(game_log_path):
                self.log.debug(f"Found Game.log in parent directory: {parent_directory}")
                return game_log_path
        except Exception as e:
            self.log.error(f"get_sc_log_path(): {e.__class__.__name__} {e}")
        return ""

    def get_sc_log_location(self, sc_launcher_path:str) -> str:
        try:
            # Search for Game.log in the folder next to StarCitizen_Launcher.exe
            star_citizen_dir = path.dirname(sc_launcher_path)
            self.log.debug(f"Searching for Game.log in directory: {star_citizen_dir}")
            log_path = self.get_sc_log_path(star_citizen_dir)

            if log_path:
                return log_path
            else:
                self.log.error("Game.log not found in expected locations.")
                return ""
        except Exception as e:
            self.log.error(f"get_sc_log_location(): {e.__class__.__name__} {e}")

    def monitor_game_state(self) -> None:
        """Continuously monitor the game state and manage log monitoring."""
        new_handle = "N/A"
        while self.program_state["enabled"]:
            try:
                game_running = self.is_game_running()

                if game_running and not self.monitoring["active"]:  # Log only when transitioning
                    self.log_parser.log_file_location = self.get_sc_log_location(self.get_sc_processes())
                    self.log.success("Star Citizen is running, Kill Tracker may proceed.")
                    self.monitoring["active"] = True

                elif game_running and self.monitoring["active"]:
                    if self.rsi_handle["current"] == "N/A":
                        # Check for current RSI handle if it does not exist
                        new_handle = self.log_parser.find_rsi_handle()
                        if new_handle != self.rsi_handle["current"] and new_handle != "N/A":
                            self.log.info(f"RSI handle name found and set to {new_handle}.")
                            self.rsi_handle["current"] = new_handle
                            self.player_geid["current"] = self.log_parser.find_rsi_geid()
                            self.log.debug(f'Current User GEID is {self.player_geid["current"]}')
                            # Handle any config changes and save them
                            self.cfg_module._set_cfg_vars()
                            self.cfg_module.migrate_old_configs()
                            # Load previous sound settings
                            is_loaded = self.cfg_module.load_cfg("volume")
                            if is_loaded == "error":
                                self.log.error("monitor_game_state(): Failed to load config.")
                            self.sounds_module.load_sound_settings()
                            self.log.info("Loaded previously saved sound settings.")
                            self.log_parser.start_tail_log_thread()
                
                elif not game_running and self.monitoring["active"]:  # Log only when transitioning to stopped
                    self.log.warning("Star Citizen has stopped.")
                    self.rsi_handle["current"] = "N/A"
                    self.player_geid["current"] = "N/A"
                    self.active_ship["current"] = "N/A"
                    self.monitoring["active"] = False

            except Exception as e:
                self.log.error(f"monitor_game_state(): {e.__class__.__name__} {e}")
            sleep(1)  # Check every second

    # DEPRECATED
    # def auto_shutdown(self, app, delay_in_seconds):
    #     def shutdown():
    #         sleep(delay_in_seconds) 
    #         self.log.warning("Application has been open for 72 hours. Shutting down in 60 seconds.")
    #         sleep(60)
    #         app.quit()
    #         exit(0) 

    #     # Run the shutdown logic in a separate thread
    #     Thread(target=shutdown, daemon=True).start()

def main():
    try:
        kt = KillTracker()
    except Exception as e:
        print(f"main(): ERROR in creating the KillTracker instance: {e.__class__.__name__} {e}")

    try:
        cfg_module = Cfg_Handler(
            kt.program_state, kt.rsi_handle
        )
    except Exception as e:
        print(f"main(): ERROR in creating the Config Handler module: {e.__class__.__name__} {e}")

    # Link Cfg Handler to main KT here (to resolve circular dependency)
    try:
        kt.cfg_module = cfg_module
    except Exception as e:
        print(f"main(): ERROR linking API to Cfg Handler: {e.__class__.__name__} {e}")

    try:
        gui_module = GUI(
            kt.cfg_module, kt.local_version, kt.anonymize_state, kt.mute_state
        )
    except Exception as e:
        print(f"main(): ERROR in creating the GUI module: {e.__class__.__name__} {e}")

    # Link GUI to other modules here (to resolve circular dependency)
    try:
        kt.cfg_module.gui = gui_module
    except Exception as e:
        print(f"main(): ERROR linking Sounds to GUI: {e.__class__.__name__} {e}")

    try:
        sound_module = Sounds(
            kt.cfg_module, kt.mute_state
        )          
    except Exception as e:
        print(f"main(): ERROR in setting up the Sounds module: {e.__class__.__name__} {e}")

    # Link Sounds to other modules here (to resolve circular dependency)
    try:
        kt.sounds_module = sound_module
        gui_module.sounds = sound_module
    except Exception as e:
        print(f"main(): ERROR linking Sounds to GUI: {e.__class__.__name__} {e}")

    try:
        api_client_module = API_Client(
            kt.cfg_module, gui_module, kt.monitoring, kt.local_version, kt.rsi_handle
        )
    except Exception as e:
        print(f"main(): ERROR in setting up the API Client module: {e.__class__.__name__} {e}")

    # Link API to Cfg Handler here (to resolve circular dependency)
    try:
        kt.cfg_module.api = api_client_module
    except Exception as e:
        print(f"main(): ERROR linking API to Cfg Handler: {e.__class__.__name__} {e}")

    try:
        cm_module = CM_Core(
            gui_module, api_client_module, kt.monitoring, kt.heartbeat_status, kt.rsi_handle, kt.active_ship, kt.update_queue
        )
    except Exception as e:
        print(f"main(): ERROR in setting up the Commander Mode Core module: {e.__class__.__name__} {e}")

    try:
        log_parser_module = LogParser(
            gui_module, api_client_module, sound_module, cm_module, kt.local_version, kt.monitoring, kt.rsi_handle, kt.player_geid, kt.active_ship, kt.anonymize_state
        )
    except Exception as e:
        print(f"main(): ERROR in setting up the Log Parser module: {e.__class__.__name__} {e}")

    try:
        game_running = kt.is_game_running()
    except Exception as e:
        print(f"main(): ERROR in checking if the game is running: {e.__class__.__name__} {e}")

    try:
        # API needs ref to some class instances for functions
        api_client_module.cm = cm_module
        # GUI needs ref to some class instances to setup the GUI
        gui_module.api = api_client_module
        gui_module.cm = cm_module
    except Exception as e:
        print(f"main(): ERROR linking Commander Mode modules: {e.__class__.__name__} {e}")

    try:
        # Load sound settings
        sound_module.load_sound_settings()
    except Exception as e:
        print(f"main(): ERROR in setting up Sound settings: {e.__class__.__name__} {e}")
    
    try:
        # Instantiate the GUI
        gui_module.setup_gui(game_running)
    except Exception as e:
        print(f"main(): ERROR in setting up the GUI: {e.__class__.__name__} {e}")

    if game_running:
        try:
            #TODO Make a module import framework to easily add in future modules
            kt.log_parser = log_parser_module
            # Add logger ref to classes
            kt.log = gui_module.log
            kt.cfg_module.log = gui_module.log
            api_client_module.log = gui_module.log
            sound_module.log = gui_module.log
            cm_module.log = gui_module.log
            log_parser_module.log = gui_module.log
        except Exception as e:
            print(f"main(): ERROR in setting up the app loggers: {e.__class__.__name__} {e}")

        try:
            sound_module.setup_sounds()
        except Exception as e:
            print(f"main(): ERROR in setting up the sounds module: {e.__class__.__name__} {e}")

        try:
            # Kill Tracker log pickler
            pickler_thr = Thread(target=kt.cfg_module.log_pickler, daemon=True).start()
        except Exception as e:
            print(f"main(): ERROR starting log pickler: {e.__class__.__name__} {e}")

        try:
             # Kill Tracker monitor loop
            monitor_thr = Thread(target=kt.monitor_game_state, daemon=True).start()
            #kt.auto_shutdown(gui_module.app, 72 * 60 * 60)
        except Exception as e:
            print(f"main(): ERROR starting game state monitoring: {e.__class__.__name__} {e}")

    try:
        # GUI main loop
        gui_module.app.mainloop()
        # Ensure all threads are stopped
        kt.program_state["enabled"] = False
    except KeyboardInterrupt:
        print("Program interrupted. Exiting gracefully...")
        kt.monitoring["active"] = False
        if isinstance(pickler_thr, Thread):
            pickler_thr.join(1)
        if isinstance(monitor_thr, Thread):
            monitor_thr.join(1)
        gui_module.app.quit()
    except Exception as e:
        print(f"main(): ERROR starting GUI main loop: {e.__class__.__name__} {e}")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"__main__: ERROR: {e.__class__.__name__} {e}")
