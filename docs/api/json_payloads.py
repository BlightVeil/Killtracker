api_key_data = {
    "api_key": self.api_key,
    "player_name": self.rsi_handle
}

api_key_exp_time = {
    "player_name": self.rsi_handle
}

kill_result = {
    "result": "exclusion"/"own_death"/"other_kill",
    "data": {
        "player": target_name,
        "victim": killed,
        "time": kill_time,
        "zone": killed_zone,
        "weapon": weapon,
        "rsi_profile": rsi_profile,
        "game_mode": self.game_mode,
        "client_ver": "7.0",
        "killers_ship": self.active_ship["current"],
        "anonymize_state": self.anonymize_state
    }
}

heartbeart_base = {
    'is_heartbeat': True,
    'player': self.rsi_handle["current"],
    'zone': self.active_ship["current"],
    'client_ver': "7.0",
    'status': status,
    'mode': "commander"
}

url = f"{self.api_fqdn}/validateKey"
heartbeat_death = {
    "is_heartbeat": True,
    "player": target_name,
    "zone": killed_zone,
    "client_ver": "7.0",
    "status": "dead",  # Report status as "dead"
    "mode": "commander"
}

heartbeat_enter_ship = {
    'is_heartbeat': True,
    'player': self.rsi_handle,
    'zone': self.player_ship,
    'client_ver': "7.0",
    'status': "alive",  # Report status as 'alive'
    'mode': "commander"
}