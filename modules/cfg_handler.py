import base64
import json
from time import sleep
from pathlib import Path

class Cfg_Handler():
    """Config Handler for the Kill Tracker."""
    def __init__(self):
        self.log = None
        self.api = None
        self.old_cfg_path = Path.cwd() / "killtracker_key.cfg"
        self.cfg_path = Path.cwd() / "bv_killtracker.cfg"
        self.cfg_dict = {"key": "", "volume": {"level": 0.5, "is_muted": False}, "pickle": []}

    def load_cfg(self, data_type:str) -> str:
        """Load the Cfg file."""
        # v1.5 Backwards compatibility
        if data_type == "key":
            if self.old_cfg_path.exists():
                with open(str(self.old_cfg_path), "r") as f:
                    entered_key = f.readline().strip()
                    if entered_key:
                        print(f"Kill Tracker v1.5 saved key loaded: {entered_key}")
                        self.cfg_dict["key"] = entered_key
                #self.old_cfg_path.unlink()
                print(f"Removed old Kill Tracker v1.5 key.")
                return self.cfg_dict[data_type]
        
        if self.cfg_path.exists():
            with open(str(self.cfg_path), "r") as f:
                cfg_base64_bytes = f.readline().strip().encode('ascii')
                cfg_bytes = base64.b64decode(cfg_base64_bytes)
                cfg_str = cfg_bytes.decode('ascii')
                self.cfg_dict = json.loads(cfg_str)

                log_line = f"load_cfg(): cfg: {self.cfg_dict}"
                if self.log:
                    self.log.debug(log_line)
                else:
                    print(log_line)
            if self.cfg_dict[data_type]:
                log_line = f"Saved {data_type} loaded: {self.cfg_dict[data_type]}"
                if self.log:
                    self.log.success(log_line)
                else:
                    print(log_line)
            else:
                log_line = f"No saved {data_type} found in file."
                if self.log:
                    self.log.warning(log_line)
                else:
                    print(log_line)
                return "error"
        return self.cfg_dict[data_type]
    
    def save_cfg(self, data_type:str, data) -> None:
        """Save the Cfg file."""
        try:
            self.cfg_dict[data_type] = data
            self.log.debug(f"save_cfg(): Saving cfg dict: {self.cfg_dict}")
            with open(str(self.cfg_path), "w") as f:
                cfg_str = json.dumps(self.cfg_dict)
                cfg_bytes = cfg_str.encode('ascii')
                cfg_base64 = base64.b64encode(cfg_bytes)
                base64_cfg = cfg_base64.decode('ascii')
                f.write(base64_cfg)
                self.log.debug(f"Successfully saved config to {str(self.cfg_path)}.")
        except FileNotFoundError as e:
            self.log.error(f"Was not able to save the config to {str(self.cfg_path)} - {e}.")

    def log_pickler(self) -> None:
        """Pickle and unpickle kill logs."""
        while True: # FIXME NEEDS BREAK CONDITION?
            try:
                if len(self.cfg_dict["pickle"]) > 0:
                    self.log.debug(f'Current buffer: {self.cfg_dict["pickle"]}.')
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