import re
from time import sleep
from os import stat
from threading import Thread

class LogParser():
    """Parses the game.log file for Star Citizen."""
    def __init__(self, gui_module, api_client_module, sound_module, cm_module, local_version, monitoring, rsi_handle, player_geid, active_ship, anonymize_state):
        self.log = None
        self.gui = gui_module
        self.api = api_client_module
        self.sounds = sound_module
        self.cm = cm_module
        self.local_version = local_version
        self.monitoring = monitoring
        self.rsi_handle = rsi_handle
        self.active_ship = active_ship
        if not self.active_ship.get("current"):
            self.active_ship["current"] = "FPS"
        self.active_ship_id = "N/A"
        self.anonymize_state = anonymize_state
        self.game_mode = "Nothing"
        self.active_ship_id = "N/A"
        self.player_geid = player_geid
        self.log_file_location = None
        self.curr_killstreak = 0
        self.max_killstreak = 0
        self.kill_total = 0
        self.death_total = 0
        
        self.global_ship_list = [
            'DRAK', 'ORIG', 'AEGS', 'ANVL', 'CRUS', 'BANU', 'MISC',
            'KRIG', 'XNAA', 'ARGO', 'VNCL', 'ESPR', 'RSI', 'CNOU',
            'GRIN', 'TMBL', 'GAMA'
        ]

    def start_tail_log_thread(self) -> None:
        """Start the log tailing in a separate thread only if it's not already running."""
        thr = Thread(target=self.tail_log, daemon=True)
        thr.start()

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
            self.log.warning("Enter Kill Tracker Key to establish Servitor connection...")
            sleep(1)
            while self.monitoring["active"]:
                # Block loop until API key is valid
                if self.api.api_key["value"]:
                    break
                sleep(1)
            self.log.debug(f"tail_log(): Received key: {self.api.api_key}. Moving on...")
        except Exception as e:
            self.log.error(f"Error waiting for Servitor connection to be established: {e.__class__.__name__} {e}")

        try:
            # Read all lines to find out what game mode player is currently, in case they booted up late.
            # Don't upload kills, we don't want repeating last session's kills in case they are actually available.
            self.log.info("Loading old log (if available)! Note that old kills shown will not be uploaded as they are stale.")
            lines = sc_log.readlines()
            for line in lines:
                if not self.api.api_key["value"]:
                    self.log.error("Error: key is invalid. Loading old log stopped.")
                    break
                self.read_log_line(line, False)
            # After loading old log, always default to FPS on the label
            self.active_ship["current"] = "FPS"
            self.active_ship_id = "N/A"
            self.gui.update_vehicle_status("FPS")
        except Exception as e:
            self.log.error(f"Error reading old log file: {e.__class__.__name__} {e}")
        
        try:
            # Main loop to monitor the log
            last_log_file_size = stat(self.log_file_location).st_size
            self.log.debug(f"tail_log(): Last log size: {last_log_file_size}.")
            self.log.success("Kill Tracking initiated.")
            self.log.success("Go Forth And Slaughter...")
        except Exception as e:
            self.log.error(f"Error getting log file size: {e.__class__.__name__} {e}")
        
        while self.monitoring["active"]:
            try:
                if not self.api.api_key["value"]:
                    self.log.error("Error: key is invalid. Kill Tracking is not active...")
                    sleep(5)
                    continue
                # Handle RSI handle first before continuing
                if self.rsi_handle["current"] == "N/A":
                    self.log.error(f"RSI handle name has not been found yet. Retrying ...")
                    self.rsi_handle["current"] = self.find_rsi_handle()
                    if self.rsi_handle["current"] != "N/A":
                        self.log.success(f"Refound RSI handle name: {self.rsi_handle['current']}.")
                where = sc_log.tell()
                line = sc_log.readline()
                if not line:
                    sleep(1)
                    sc_log.seek(where)
                    if last_log_file_size > stat(self.log_file_location).st_size:
                        sc_log.close()
                        sc_log = open(self.log_file_location, "r")
                        last_log_file_size = stat(self.log_file_location).st_size
                else:
                    self.read_log_line(line, True)
            except Exception as e:
                self.log.error(f"Error reading game log file: {e.__class__.__name__} {e}")
        self.log.info("Game log monitoring has stopped.")

    def _extract_ship_info(self, line):
        match = re.search(r"for '([\w]+(?:_[\w]+)+)_(\d+)'", line)
        if match:
            ship_type = match.group(1)
            ship_id = match.group(2)
            return {"ship_type": ship_type, "ship_id": ship_id}
        return None

    def read_log_line(self, line: str, upload_kills: bool) -> None:
        if upload_kills and "<Vehicle Control Flow>" in line:
                if (
                    ("CVehicleMovementBase::SetDriver:" in line and "requesting control token for" in line) or
                    ("CVehicle::Initialize::<lambda_1>::operator ():" in line and "granted control token for" in line)
                ):
                    ship_data = self._extract_ship_info(line)
                    if ship_data:
                        self.active_ship["current"] = ship_data["ship_type"]
                        self.active_ship_id = ship_data["ship_id"]
                        self.log.info(f"Entered ship: {self.active_ship['current']} (ID: {self.active_ship_id})")
                        self.gui.update_vehicle_status(self.active_ship["current"])
                    return
                if (
                    ("CVehicleMovementBase::ClearDriver:" in line and "releasing control token for" in line) or
                    ("losing control token for" in line)
                ):
                    self.active_ship["current"] = "FPS"
                    self.active_ship_id = "N/A"
                    self.log.info("Exited ship: Defaulted to FPS (on-foot)")
                    self.gui.update_vehicle_status("FPS")
                    return
                
        if "<Context Establisher Done>" in line:
            self.set_game_mode(line)
            self.log.debug(f"read_log_line(): set_game_mode with: {line}.")
        elif "CPlayerShipRespawnManager::OnVehicleSpawned" in line and (
                "SC_Default" != self.game_mode) and (self.player_geid["current"] in line):
            self.set_ac_ship(line)
            self.log.debug(f"read_log_line(): set_ac_ship with: {line}.")
        elif ("<Vehicle Destruction>" in line or
            "<local client>: Entering control state dead" in line) and (
                self.active_ship_id in line):
            self.log.debug(f"read_log_line(): destroy_player_zone with: {line}")
            self.destroy_player_zone()
        elif self.rsi_handle["current"] in line:
            if "OnEntityEnterZone" in line:
                self.log.debug(f"read_log_line(): set_player_zone with: {line}.")
                self.set_player_zone(line, False)
            if "CActor::Kill" in line and not self.check_ignored_victims(line) and upload_kills:
                kill_result = self.parse_kill_line(line, self.rsi_handle["current"])
                self.log.debug(f"read_log_line(): kill_result with: {line}.")
                # Do not send
                if kill_result["result"] == "exclusion" or kill_result["result"] == "reset":
                    self.log.debug(f"read_log_line(): Not posting {kill_result['result']} death: {line}.")
                    return
                # Log a message for the current user's death
                elif kill_result["result"] == "killed" or kill_result["result"] == "suicide":
                    self.curr_killstreak = 0
                    self.gui.curr_killstreak_label.config(text=f"Current Killstreak: {self.curr_killstreak}", fg="yellow")
                    self.death_total += 1
                    self.gui.session_deaths_label.config(text=f"Total Session Deaths: {self.death_total}", fg="red")
                    self.log.info("You have fallen in the service of BlightVeil.")
                    if kill_result["result"] == "killed":
                        self.log.info(f'You were killed by {kill_result["data"]["killer"]} with {kill_result["data"]["weapon"]}.')
                    # Send death-event to the server via heartbeat
                    self.cm.post_heartbeat_event(kill_result["data"]["victim"], kill_result["data"]["zone"], None)
                    self.destroy_player_zone()
                    self.update_kd_ratio()
                    if kill_result["result"] == "killed" and self.game_mode == "EA_FreeFlight":
                        death_result = self.parse_death_line(line, self.rsi_handle["current"])
                        self.api.post_kill_event(death_result, "reportACKill")
                # Log a message for the current user's kill
                elif kill_result["result"] == "killer":
                    self.curr_killstreak += 1
                    if self.curr_killstreak > self.max_killstreak:
                        self.max_killstreak = self.curr_killstreak
                    self.kill_total += 1
                    self.gui.curr_killstreak_label.config(text=f"Current Killstreak: {self.curr_killstreak}", fg="#04B431")
                    self.gui.max_killstreak_label.config(text=f"Max Killstreak: {self.max_killstreak}", fg="#04B431")
                    self.gui.session_kills_label.config(text=f"Total Session Kills: {self.kill_total}", fg="#04B431")
                    self.log.success(f"You have killed {kill_result['data']['victim']},")
                    self.log.info(f"and brought glory to BlightVeil.")
                    self.sounds.play_random_sound()
                    self.api.post_kill_event(kill_result, "reportKill")
                    self.update_kd_ratio()
                else:
                    self.log.error(f"Kill failed to parse: {line}")
        elif "<Jump Drive State Changed>" in line:
            self.log.debug(f"read_log_line(): set_player_zone with: {line}.")
            self.set_player_zone(line, True)

    def set_game_mode(self, line:str) -> None:
        """Parse log for current active game mode."""
        split_line = line.split(' ')
        curr_game_mode = split_line[8].split("=")[1].strip("\"")
        if self.game_mode != curr_game_mode:
            self.game_mode = curr_game_mode
        if "SC_Default" == curr_game_mode:
            self.active_ship["current"] = "FPS"
            self.active_ship_id = "N/A"
            self.gui.update_vehicle_status("FPS")

    def set_ac_ship(self, line:str) -> None:
        """Parse log for current active ship."""
        self.active_ship["current"] = line.split(' ')[5][1:-1]
        self.log.debug(f"Player has entered ship: {self.active_ship['current']}")
        self.gui.update_vehicle_status(self.active_ship["current"])

    def destroy_player_zone(self) -> None:
        self.log.debug(f"Ship Destroyed: {self.active_ship['current']} with ID: {self.active_ship_id}")
        self.active_ship["current"] = "FPS"
        self.active_ship_id = "N/A"
        self.gui.update_vehicle_status("FPS")

    def set_player_zone(self, line: str, use_jd) -> None:
        """Set current active ship zone."""
        if not use_jd:
            line_index = line.index("-> Entity ") + len("-> Entity ")
        else:
            line_index = line.index("adam: ") + len("adam: ")
        if 0 == line_index:
            self.log.debug(f"Active Zone Change: {self.active_ship['current']}")
            self.active_ship["current"] = "FPS"
            self.gui.update_vehicle_status("FPS")
            return
        if not use_jd:
            potential_zone = line[line_index:].split(' ')[0]
            potential_zone = potential_zone[1:-1]
        else:
            potential_zone = line[line_index:].split(' ')[0]
        for x in self.global_ship_list:
            if potential_zone.startswith(x):
                self.active_ship["current"] = potential_zone[:potential_zone.rindex('_')]
                self.active_ship_id = potential_zone[potential_zone.rindex('_') + 1:]
                self.log.debug(f"Active Zone Change: {self.active_ship['current']} with ID: {self.active_ship_id}")
                self.cm.post_heartbeat_event(None, None, self.active_ship["current"])
                self.gui.update_vehicle_status(self.active_ship["current"])
                return
      
    def check_ignored_victims(self, line) -> bool:
        """Check if any ignored victims are present in the given line."""
        for data in self.api.sc_data["ignoredVictimRules"]:
            if data["value"].lower() in line.lower():
                self.log.debug(f"Found the human readable string: {data['value']} in the raw log string: {line}")
                return True
        return False

    def check_exclusion_scenarios(self, line:str) -> bool:
        """Check for kill edgecase scenarios."""
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
    
    def get_sc_data(self, data_type:str, data_id:str) -> str:
        """Get the human readable string from the parsed log value."""
        try:
            for data in self.api.sc_data[data_type]:
                if data["id"] in data_id:
                    self.log.debug(f"Found the human readable string: {data['name']} of the raw log string: {data_id}")
                    return data["name"]
            self.log.warning(f"Did not find the human readable version of the raw log string: {data_id}")
        except Exception as e:
            self.log.error(f"get_weapon(): Error: {e.__class__.__name__} {e}")
            return data_id

    def parse_kill_line(self, line:str, curr_user:str):
        """Parse kill event."""
        try:
            kill_result = {"result": "", "data": {}}

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

            if killed == killer:
                # Current user killed themselves
                kill_result["result"] = "suicide"
                kill_result["data"] = {
                    'player': curr_user,
                    'weapon': weapon,
                    'zone': killed_zone
                }
            elif killed == curr_user:
                mapped_weapon = self.get_sc_data("weapons", weapon)
                # Current user died
                kill_result["result"] = "killed"
                kill_result["data"] = {
                    'player': curr_user,
                    'victim': curr_user,
                    'killer': killer,
                    'weapon': mapped_weapon,
                    'zone': self.active_ship["current"]
                }
            elif killer.lower() == "unknown":
                # Potential Ship reset
                kill_result["result"] = "reset"
            else:
                # Current user killed other player
                kill_result["result"] = "killer"
                kill_result["data"] = {
                    'player': curr_user,
                    'victim': killed,
                    'time': kill_time,
                    'zone': killed_zone,
                    'weapon': weapon,
                    'rsi_profile': rsi_profile,
                    'game_mode': self.game_mode,
                    'client_ver': self.local_version,
                    'killers_ship': self.active_ship["current"],
                    'anonymize_state': self.anonymize_state
                }
            return kill_result
        except Exception as e:
            self.log.error(f"parse_kill_line(): Error: {e.__class__.__name__} {e}")
            return {"result": "", "data": None}

    def parse_death_line(self, line:str, curr_user:str):
        """Parse death event."""
        try:
            death_result = {"result": "", "data": {}}

            if not self.check_exclusion_scenarios(line):
                death_result["result"] = "exclusion"
                return death_result

            split_line = line.split(' ')

            kill_time = split_line[0].strip('\'')
            killer = split_line[12].strip('\'')

            death_result["result"] = "killed"
            death_result["data"] = {
                'time': kill_time,
                'player': killer,
                'victim': curr_user,
                'game_mode': self.game_mode,
            }
            return death_result
        except Exception as e:
            self.log.error(f"parse_kill_line(): Error: {e.__class__.__name__} {e}")
            return {"result": "", "data": None}

    def find_rsi_handle(self) -> str:
        """Get the current user's RSI handle."""
        acct_str = "<Legacy login response> [CIG-net] User Login Success"
        sc_log = open(self.log_file_location, "r")
        lines = sc_log.readlines()
        for line in lines:
            if -1 != line.find(acct_str):
                line_index = line.index("Handle[") + len("Handle[")
                if 0 == line_index:
                    self.log.error("RSI Handle not found. Please ensure the game is running and the log file is accessible.")
                    self.gui.api_status_label.config(text="Key Status: Error", fg="yellow")
                    return "N/A"
                potential_handle = line[line_index:].split(' ')[0]
                return potential_handle[0:-1]
        self.log.error("RSI Handle not found. Please ensure the game is running and the log file is accessible.")
        self.gui.api_status_label.config(text="Key Status: Error", fg="yellow")
        return "N/A"

    def find_rsi_geid(self) -> str:
        """Get the current user's GEID."""
        acct_kw = "AccountLoginCharacterStatus_Character"
        sc_log = open(self.log_file_location, "r")
        lines = sc_log.readlines()
        for line in lines:
            if -1 != line.find(acct_kw):
                return line.split(' ')[11]
                
    def update_kd_ratio(self) -> None:
        """Update KDR."""
        self.log.debug(f"update_kd_ratio(): Kills={self.kill_total}, Deaths={self.death_total}")
        if self.kill_total == 0 and self.death_total == 0:
            kd_display = "--"
        elif self.death_total == 0:
            kd_display = "∞"
        else:
            kd = self.kill_total / self.death_total
            kd_display = f"{kd:.2f}"
        # Update the KD label in the GUI
        if hasattr(self.gui, 'kd_ratio_label'):
            self.gui.kd_ratio_label.config(text=f"KD Ratio: {kd_display}", fg="#00FFFF")

    def handle_player_death(self) -> None:
        """Handle KDR when user dies."""
        self.curr_killstreak = 0
        self.death_total += 1
        # ... other updates ...
        self.update_kd_ratio()

    def handle_player_kill(self) -> None:
        """Handle KDR when user gets a kill."""
        self.curr_killstreak += 1
        if self.curr_killstreak > self.max_killstreak:
            self.max_killstreak = self.curr_killstreak
        self.kill_total += 1
        # ... other updates ...
        self.update_kd_ratio()