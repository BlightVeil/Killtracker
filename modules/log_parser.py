import time
import os
import threading

class LogParser():
    """Parses the game.log file for Star Citizen."""
    def __init__(self, logger, log_file_location: str) -> None:
        self.log = logger
        self.log_file_location = log_file_location
        self.game_mode = "Nothing"
        self.active_ship = "N/A"
        self.active_ship_id = "N/A"
        self.player_geid = "N/A"
                
        self.global_ship_list = [
            'DRAK', 'ORIG', 'AEGS', 'ANVL', 'CRUS', 'BANU', 'MISC',
            'KRIG', 'XNAA', 'ARGO', 'VNCL', 'ESPR', 'RSI', 'CNOU',
            'GRIN', 'TMBL', 'GAMA'
        ]
        # Substrings to ignore
        self.ignore_kill_substrings = [
            'PU_Pilots',
            'NPC_Archetypes',
            'PU_Human',
            'kopion',
            'marok',
        ]

    def start_tail_log_thread(self, log_file_location, rsi_name, logger):
        """Start the log tailing in a separate thread only if it's not already running."""
        thread = threading.Thread(target=self.tail_log, args=(log_file_location, rsi_name, logger))
        thread.daemon = True
        thread.start()

    def async_loading_animation(self, app) -> None:
        def animate():
            for dots in [".", "..", "..."]:
                self.log.info(dots)
                app.update_idletasks()
                time.sleep(0.2)
        threading.Thread(target=animate, daemon=True).start()
        
    def destroy_player_zone(self) -> None:
        if ("N/A" != self.active_ship) or ("N/A" != self.active_ship_id):
            self.log.debug(f"Ship Destroyed: {self.active_ship} with ID: {self.active_ship_id}")
            self.active_ship = "N/A"
            self.active_ship_id = "N/A"

    def set_ac_ship(self, line: str) -> None:
        self.active_ship = line.split(' ')[5][1:-1]
        self.log.debug("Player has entered ship: ", self.active_ship)

    def set_player_zone(self, line: str) -> None:
        line_index = line.index("-> Entity ") + len("-> Entity ")
        if 0 == line_index:
            self.log.debug("Active Zone Change: ", self.active_ship)
            self.active_ship = "N/A"
            return
        potential_zone = line[line_index:].split(' ')[0]
        potential_zone = potential_zone[1:-1]
        for x in self.global_ship_list:
            if potential_zone.startswith(x):
                self.active_ship = potential_zone[:potential_zone.rindex('_')]
                self.active_ship_id = potential_zone[potential_zone.rindex('_') + 1:]
                self.log.debug(f"Active Zone Change: {self.active_ship} with ID: {self.active_ship_id}")
                if self.heartbeat_active:
                    self.post_heartbeat_enter_ship_event()
                return

    def check_substring_list(self, line, substring_list: list) -> bool:
        """Check if any substring from the list is present in the given line."""
        for substring in substring_list:
            if substring.lower() in line.lower():
                return True
        return False

    def check_exclusion_scenarios(self, line: str) -> bool:        
        if self.game_mode == "EA_FreeFlight":
            if "Crash" in line:
                self.log.info("Probably a ship reset, ignoring kill!")
                return False
            if "SelfDestruct" in line:
                self.log.info("Self-destruct detected in Free Flight, ignoring kill!")
                return False

        elif self.game_mode == "EA_SquadronBattle":
            # Add your specific conditions for Squadron Battle mode
            if "Crash" in line:
                self.log.info("Crash detected in Squadron Battle, ignoring kill!")
                return False
            if "SelfDestruct" in line:
                self.log.info("Self-destruct detected in Squadron Battle, ignoring kill!")
                return False
        return True
    
    # Event checking logic. Look for substrings, do stuff based on what we find.
    def read_log_line(self, line, rsi_handle, upload_kills) -> None:
        if -1 != line.find("<Context Establisher Done>"):
            self.set_game_mode(line)
        elif -1 != line.find("CPlayerShipRespawnManager::OnVehicleSpawned") and (
                "SC_Default" != self.game_mode) and (-1 != line.find(self.player_geid)):
            self.set_ac_ship(line)
        elif ((-1 != line.find("<Vehicle Destruction>")) or (
                -1 != line.find("<local client>: Entering control state dead"))) and (
                -1 != line.find(self.active_ship_id)):
            self.destroy_player_zone(line)
        elif -1 != line.find(rsi_handle):
            if -1 != line.find("OnEntityEnterZone"):
                self.set_player_zone(line)
            if -1 != line.find("CActor::Kill") and not self.check_substring_list(line, self.ignore_kill_substrings) and upload_kills:
                self.parse_kill_line(line, rsi_handle) ,,,,

    def tail_log(self, rsi_name) -> None:
        """Read the log file and display events in the GUI."""
        sc_log = open(self.log_file_location, "r")
        if sc_log is None:
            self.log.error(f"No log file found at {self.log_file_location}.")
            return
        self.log.success("Kill Tracking Initiated...")
        self.log.warning("Enter key to establish Servitor connection...")

        # Read all lines to find out what game mode player is currently, in case they booted up late.
        # Don't upload kills, we don't want repeating last sessions kills incase they are actually available.
        lines = sc_log.readlines()
        self.log.warning("Loading old log (if available)! Kills shown will not be uploaded as they are stale.")
        for line in lines:
            self.read_log_line(line, rsi_name, False)

        # Main loop to monitor the log
        last_log_file_size = os.stat(self.log_file_location).st_size
        while True:
            where = sc_log.tell()
            line = sc_log.readline()
            if not line:
                time.sleep(1)
                sc_log.seek(where)
                if last_log_file_size > os.stat(self.log_file_location).st_size:
                    sc_log.close()
                    sc_log = open(self.log_file_location, "r")
                    last_log_file_size = os.stat(self.log_file_location).st_size
            else:
                self.read_log_line(line, rsi_name, True)
        
    def read_existing_log(self, rsi_name) -> None:
        sc_log = open(self.log_file_location, "r")
        lines = sc_log.readlines()
        for line in lines:
            self.read_log_line(self, line, rsi_name, True)

    def find_rsi_handle(self) -> str:
        acct_str = "<Legacy login response> [CIG-net] User Login Success"
        sc_log = open(self.log_file_location, "r")
        lines = sc_log.readlines()
        for line in lines:
            if -1 != line.find(acct_str):
                line_index = line.index("Handle[") + len("Handle[")
                if 0 == line_index:
                    self.log.error("RSI HANDLE: Not Found!")
                    return ""
                potential_handle = line[line_index:].split(' ')[0]
                return potential_handle[0:-1]
        self.log.error("RSI HANDLE: Not Found!")
        return ""

    def find_rsi_geid(self) -> None:
        acct_kw = "AccountLoginCharacterStatus_Character"
        sc_log = open(self.log_file_location, "r")
        lines = sc_log.readlines()
        for line in lines:
            if -1 != line.find(acct_kw):
                self.player_geid = line.split(' ')[11]
                self.log.debug(f"Player geid: {self.player_geid}")
                return

    def set_game_mode(self, line: str) -> None:
        """Parse log for current active game mode."""
        split_line = line.split(' ')
        curr_game_mode = split_line[8].split("=")[1].strip("\"")
        if self.game_mode != curr_game_mode:
            self.game_mode = curr_game_mode

        if "SC_Default" == curr_game_mode:
            self.active_ship = "N/A"
            self.active_ship_id = "N/A"
