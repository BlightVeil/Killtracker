import base64
import json
from time import sleep

class Cfg_Handler():
    """Config Handler for the Kill Tracker."""
    def __init__(self):
        self.log = None
        self.api = None
        self.cfg_filename = "bv_killtracker.cfg"
        self.cfg_dict = {"key": "", "volume": {"level": 0.5, "is_muted": False}, "pickle": []}, 

    def load_cfg(self, data_type:str) -> str:
        """Load the Cfg file."""
        with open(self.cfg_filename, "r") as f:
            cfg_base64_bytes = f.readline().strip().encode('ascii')
            cfg_bytes = base64.b64decode(cfg_base64_bytes)
            cfg_str = cfg_bytes.decode('ascii')
            self.cfg_dict = json.loads(cfg_str)
            self.log.debug(f"load_cfg(): cfg: {self.cfg_dict}")
        if self.cfg_dict[data_type]:
            self.log.success(f"Saved {data_type} loaded: {self.cfg_dict[data_type]}.")
        else:
            self.log.warning(f"No saved {data_type} found in file.")
            return "error"
        return self.cfg_dict[data_type]
    
    def save_cfg(self, data_type:str, data) -> None:
        """Save the Cfg file."""
        try:
            self.cfg_dict[data_type] = data
            self.log.debug(f"save_cfg(): Saving cfg dict: {self.cfg_dict}")
            with open(self.cfg_filename, "w") as f:
                cfg_str = json.dumps(self.cfg_dict)
                cfg_bytes = cfg_str.encode('ascii')
                cfg_base64 = base64.b64encode(cfg_bytes)
                base64_cfg = cfg_base64.decode('ascii')
                f.write(base64_cfg)
                self.log.debug(f"Successfully saved config to {self.cfg_filename}.")
        except FileNotFoundError as e:
            self.log.error(f"Was not able to save the config to {self.cfg_filename} - {e}.")

    def log_pickler(self) -> None:
        """Pickle and unpickle kill logs."""
        while True: # FIXME NEEDS BREAK CONDITION?
            try:
                if len(self.cfg_dict["pickle"]) > 0:
                    self.save_cfg("pickle", self.cfg_dict["pickle"])
                    if self.api.connection_healthy:
                        kill = self.cfg_dict["pickle"][0]
                        self.log.info(f"Attempting to post a previous kill from the buffer: {kill}.")
                        uploaded = self.api.post_kill_event(kill)
                        if uploaded:
                            self.cfg_dict["pickle"].pop(0)
                            self.save_cfg("pickle", self.cfg_dict["pickle"])
            except Exception as e:
                self.log.error(f"log_pickler(): Error: {e.__class__.__name__} {e}")
            sleep(5)  # Check every 5 seconds