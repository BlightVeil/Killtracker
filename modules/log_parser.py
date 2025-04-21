import time
import os
import threading

class LogParser():
    """Parses the game.log file for Star Citizen."""
    def __init__(self, logger, api_client_module, sound_module, cm_api_module, log_file_location, rsi_handle, active_ship):
        self.log = logger
        self.api = api_client_module
        self.sounds = sound_module
        self.cm_api = cm_api_module
        self.log_file_location = log_file_location
        self.rsi_handle = rsi_handle
        self.active_ship = active_ship
        self.game_mode = "Nothing"
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

    def start_tail_log_thread(self) -> None:
        """Start the log tailing in a separate thread only if it's not already running."""
        thread = threading.Thread(target=self.tail_log, args=())
        thread.daemon = True
        thread.start()

    def tail_log(self) -> None:
        """Read the log file and display events in the GUI."""
        try:
            sc_log = open(self.log_file_location, "r")
            if sc_log is None:
                self.log.error(f"No log file found at {self.log_file_location}")
                return
        except Exception as e:
            self.log.error(f"Error opening log file: {e.__class__.__name__} {e}")

        try:
            self.log.success("Kill Tracking initiated...")
            self.log.warning("Enter API key to establish Servitor connection...")
            # Read all lines to find out what game mode player is currently, in case they booted up late.
            # Don't upload kills, we don't want repeating last session's kills in case they are actually available.
            lines = sc_log.readlines()
            self.log.info("Loading old log (if available)! Note that old kills shown will not be uploaded as they are stale.")
            for line in lines:
                if not self.api_key["value"]:
                    self.log.error("Error: API key is invalid. Loading old log stopped.")
                    break
                self.read_log_line(line, False)

            # Main loop to monitor the log
            last_log_file_size = os.stat(self.log_file_location).st_size
            while True:
                if not self.api_key["value"]:
                    self.log.error("Error: API key is invalid. Kill Tracking stopped...")
                    break
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
                    self.read_log_line(line, True)
        except Exception as e:
            self.log.error(f"Error tailing log file: {e.__class__.__name__} {e}")

    def read_log_line(self, line, upload_kills) -> None:
        """Event checking logic. Look for substrings, do stuff based on what we find."""
        if -1 != line.find("<Context Establisher Done>"):
            self.set_game_mode(line)
        elif -1 != line.find("CPlayerShipRespawnManager::OnVehicleSpawned") and (
                "SC_Default" != self.game_mode) and (-1 != line.find(self.player_geid)):
            self.set_ac_ship(line)
        elif ((-1 != line.find("<Vehicle Destruction>")) or (
                -1 != line.find("<local client>: Entering control state dead"))) and (
                -1 != line.find(self.active_ship_id)):
            self.destroy_player_zone()
        elif -1 != line.find(self.rsi_handle["current"]):
            if -1 != line.find("OnEntityEnterZone"):
                self.set_player_zone(line)
            if -1 != line.find("CActor::Kill") and not self.check_substring_list(line, self.ignore_kill_substrings) and upload_kills:
                kill_result = self.parse_kill_line(line, self.rsi_handle["current"])
                if kill_result["result"] == "exclusion":
                    return
                elif kill_result["result"] == "own_death":
                    # Log a message for the player's own death
                    self.log.info("You have fallen in the service of BlightVeil.")
                    # Send death-event to the server via heartbeat
                    self.cm_api.post_heartbeat_death_event(kill_result["data"]["player"], kill_result["data"]["zone"])
                    self.destroy_player_zone()
                elif kill_result["result"] == "other_kill":
                    self.log.success(f"You have killed {kill_result['data']['victim']},")
                    self.log.info(f"and brought glory to BlightVeil.")
                    self.sounds.play_random_sound()
                    self.api.post_kill_event(kill_result)

    def set_game_mode(self, line: str) -> None:
        """Parse log for current active game mode."""
        split_line = line.split(' ')
        curr_game_mode = split_line[8].split("=")[1].strip("\"")
        if self.game_mode != curr_game_mode:
            self.game_mode = curr_game_mode

        if "SC_Default" == curr_game_mode:
            self.active_ship["current"] = "N/A"
            self.active_ship_id = "N/A"

    def set_ac_ship(self, line: str) -> None:
        """Parse log for current active ship."""
        self.active_ship["current"] = line.split(' ')[5][1:-1]
        self.log.debug("Player has entered ship: ", self.active_ship["current"])
    
    def destroy_player_zone(self) -> None:
        if ("N/A" != self.active_ship["current"]) or ("N/A" != self.active_ship_id):
            self.log.debug(f"Ship Destroyed: {self.active_ship['current']} with ID: {self.active_ship_id}")
            self.active_ship["current"] = "N/A"
            self.active_ship_id = "N/A"

    def set_player_zone(self, line: str) -> None:
        line_index = line.index("-> Entity ") + len("-> Entity ")
        if 0 == line_index:
            self.log.debug(f"Active Zone Change: {self.active_ship['current']}")
            self.active_ship["current"] = "N/A"
            return
        potential_zone = line[line_index:].split(' ')[0]
        potential_zone = potential_zone[1:-1]
        for x in self.global_ship_list:
            if potential_zone.startswith(x):
                self.active_ship["current"] = potential_zone[:potential_zone.rindex('_')]
                self.active_ship_id = potential_zone[potential_zone.rindex('_') + 1:]
                self.log.debug(f"Active Zone Change: {self.active_ship['current']} with ID: {self.active_ship_id}")
                self.cm_api.post_heartbeat_enter_ship_event(self.active_ship["current"])
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

    #FIXME unused?
    '''
    def find_rsi_geid(self) -> None:
        acct_kw = "AccountLoginCharacterStatus_Character"
        sc_log = open(self.log_file_location, "r")
        lines = sc_log.readlines()
        for line in lines:
            if -1 != line.find(acct_kw):
                self.player_geid = line.split(' ')[11]
                self.log.debug(f"Player geid: {self.player_geid}")
                return
    '''

    def parse_kill_line(self, line, target_name):
        """ Parse kill event"""
        try:
            kill_result = {"result": "", "data": None}

            if not self.check_exclusion_scenarios(line):
                kill_result["result"] = "exclusion"
                return kill_result
            
            split_line = line.split(' ')

            kill_time = split_line[0].strip('\'')
            killed = split_line[5].strip('\'')
            killed_zone = split_line[9].strip('\'')
            killer = split_line[12].strip('\'')
            weapon = split_line[15].strip('\'')
            rsi_profile = f"https://robertsspaceindustries.com/citizens/{killed}"

            if killed == killer or killer.lower() == "unknown" or killed == target_name:
                # Log a message for the player's own death
                kill_result["result"] = "own_death"
                kill_result["data"] = killed_zone
                return kill_result
            else:
                kill_result["result"] = "other_kill"
                kill_result["data"] = {
                    'player': target_name,
                    'victim': killed,
                    'time': kill_time,
                    'zone': killed_zone,
                    'weapon': weapon,
                    'rsi_profile': rsi_profile,
                    'game_mode': self.game_mode,
                    'client_ver': "7.0",
                    'killers_ship': self.active_ship["current"],
                    'anonymize_state': self.anonymize_state
                }