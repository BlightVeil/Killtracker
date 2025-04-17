import time
import os
import threading

class LogParser():
    """
    Parses the game.log file for Star Citizen
    """
    def __init__(self, logger, log_file_location) -> None:
        self.log = logger
        self.log_file_location = log_file_location
        # Substrings to ignore
        self.ignore_kill_substrings = [
            'PU_Pilots',
            'NPC_Archetypes',
            'PU_Human',
            'kopion',
            'marok',
        ]

    def async_loading_animation(self, app):
        def animate():
            for dots in [".", "..", "..."]:
                self.log.log(dots)
                app.update_idletasks()
                time.sleep(0.2)
        threading.Thread(target=animate, daemon=True).start()
        
    def destroy_player_zone(self, line):
        global global_active_ship
        global global_active_ship_id
        if ("N/A" != global_active_ship) or ("N/A" != global_active_ship_id):
            self.log.log(f"Ship Destroyed: {global_active_ship} with ID: {global_active_ship_id}")
            global_active_ship = "N/A"
            global_active_ship_id = "N/A"

    def set_ac_ship(self, line):
        global global_active_ship
        global_active_ship = line.split(' ')[5][1:-1]
        self.log.log("Player has entered ship: ", global_active_ship)

    def set_player_zone(self, line):
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
        for x in self.global_ship_list:
            if potential_zone.startswith(x):
                global_active_ship = potential_zone[:potential_zone.rindex('_')]
                global_active_ship_id = potential_zone[potential_zone.rindex('_') + 1:]
                print(f"Active Zone Change: {global_active_ship} with ID: {global_active_ship_id}")
                if global_heartbeat_active:
                    post_heartbeat_enter_ship_event(global_rsi_handle, global_active_ship) ,,,,,,,,
                return

    def check_substring_list(self, line, substring_list):
        """Check if any substring from the list is present in the given line."""
        for substring in substring_list:
            if substring.lower() in line.lower():
                return True
        return False

    def check_exclusion_scenarios(self, line):
        global global_game_mode
        
        if global_game_mode == "EA_FreeFlight":
            if "Crash" in line:
                self.log.log("Probably a ship reset, ignoring kill!")
                return False
            if "SelfDestruct" in line:
                self.log.log("Self-destruct detected in EA_FreeFlight, ignoring kill!")
                return False

        elif global_game_mode == "EA_SquadronBattle":
            # Add your specific conditions for Squadron Battle mode
            if "Crash" in line:
                self.log.log("Crash detected in EA_SquadronBattle, ignoring kill!")
                return False
            if "SelfDestruct" in line:
                self.log.log("Self-destruct detected in EA_SquadronBattle, ignoring kill!")
                return False
        return True
    
    # Event checking logic. Look for substrings, do stuff based on what we find.
    def read_log_line(self, line, rsi_handle, upload_kills):
        if -1 != line.find("<Context Establisher Done>"):
            self.set_game_mode(line)
        elif -1 != line.find("CPlayerShipRespawnManager::OnVehicleSpawned") and (
                "SC_Default" != global_game_mode) and (-1 != line.find(global_player_geid)):
            self.set_ac_ship(line)
        elif ((-1 != line.find("<Vehicle Destruction>")) or (
                -1 != line.find("<local client>: Entering control state dead"))) and (
                -1 != line.find(global_active_ship_id)):
            self.destroy_player_zone(line)
        elif -1 != line.find(rsi_handle):
            if -1 != line.find("OnEntityEnterZone"):
                self.set_player_zone(line)
            if -1 != line.find("CActor::Kill") and not self.check_substring_list(line, self.ignore_kill_substrings) and upload_kills:
                self.parse_kill_line(line, rsi_handle) ,,,,

    def tail_log(self, rsi_name):
        """Read the log file and display events in the GUI."""
        global global_game_mode, global_player_geid
        sc_log = open(self.log_file_location, "r")
        if sc_log is None:
            self.log.log(f"No log file found at {self.log_file_location}.")
            return
        self.log.log("Kill Tracking Initiated...")
        self.log.log("Enter key to establish Servitor connection...")

        # Read all lines to find out what game mode player is currently, in case they booted up late.
        # Don't upload kills, we don't want repeating last sessions kills incase they are actually available.
        lines = sc_log.readlines()
        self.log.log("Loading old log (if available)! Kills shown will not be uploaded as they are stale.")
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
        
    def read_existing_log(self, rsi_name):
        sc_log = open(self.log_file_location, "r")
        lines = sc_log.readlines()
        for line in lines:
            self.read_log_line(self, line, rsi_name, True)

    def find_rsi_handle(self, self.log_file_location):
        acct_str = "<Legacy login response> [CIG-net] User Login Success"
        sc_log = open(self.log_file_location, "r")
        lines = sc_log.readlines()
        for line in lines:
            if -1 != line.find(acct_str):
                line_index = line.index("Handle[") + len("Handle[")
                if 0 == line_index:
                    logger.log("⚠️ RSI_HANDLE: Not Found!")
                    exit()
                potential_handle = line[line_index:].split(' ')[0]
                return potential_handle[0:-1]
        logger.log(f"❌ Error: RSI handle not found.")
        return ""

    def find_rsi_geid(self):
        global global_player_geid
        acct_kw = "AccountLoginCharacterStatus_Character"
        sc_log = open(self.log_file_location, "r")
        lines = sc_log.readlines()
        for line in lines:
            if -1 != line.find(acct_kw):
                global_player_geid = line.split(' ')[11]
                logger.log(f"Player geid: {global_player_geid}")
                return

    def set_game_mode(self, line):
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
