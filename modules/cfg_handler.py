import base64
import hashlib
import json
from time import sleep
from pathlib import Path

class Cfg_Handler:
    """Config Handler with simple XOR encryption (built-in only)."""

    def __init__(self, program_state, rsi_handle=None):
        self.log = None
        self.api = None
        self.program_state = program_state
        self.old_cfg_path = Path.cwd() / "killtracker_key.cfg"
        self.cfg_path = Path.cwd() / "bv_killtracker.cfg"
        self.cfg_dict = {"key": "", "volume": {"level": 0.5, "is_muted": False}, "pickle": []}
        self.rsi_handle = rsi_handle if rsi_handle else "default_handle"
        self.key = self._derive_key(self.rsi_handle)

    def _derive_key(self, rsi_handle: str) -> bytes:
        """Derive a 32-byte key from the RSI handle using SHA256."""
        return hashlib.sha256(rsi_handle.encode()).digest()

    def _xor_encrypt(self, data: bytes) -> bytes:
        """Simple XOR encrypt/decrypt with repeating key."""
        key = self.key
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

    def load_cfg(self, data_type: str) -> str:
        """Load the config with simple XOR decryption."""
        if data_type == "key" and self.old_cfg_path.exists():
            self.old_cfg_path.unlink()
            print(f"Removed old Kill Tracker key file.")

        if not self.cfg_path.exists():
            return self.cfg_dict.get(data_type, "error")

        try:
            with open(str(self.cfg_path), "rb") as f:
                file_data = f.read()
            try:
                # Decrypt with XOR and base64 decode
                decrypted_data = self._xor_encrypt(base64.b64decode(file_data)).decode('utf-8')
                self.cfg_dict = json.loads(decrypted_data)
                print(f"load_cfg(): cfg: {self.cfg_dict}")
                return self.cfg_dict.get(data_type, "error")
            except Exception as e:
                print(f"Failed to decrypt config: {e}")
                return "error"
        except Exception as e:
            print(f"Failed to load config file: {e}")
            return "error"

    def save_cfg(self, data_type: str, data) -> None:
        """Encrypt and save the configuration with XOR and base64."""
        try:
            self.cfg_dict[data_type] = data
            cfg_json = json.dumps(self.cfg_dict)
            encrypted_data = base64.b64encode(self._xor_encrypt(cfg_json.encode('utf-8')))
            with open(str(self.cfg_path), "wb") as f:
                f.write(encrypted_data)
            if self.log:
                self.log.debug(f"Successfully saved encrypted config to {str(self.cfg_path)}.")
        except Exception as e:
            if self.log:
                self.log.error(f"Was not able to save the config to {str(self.cfg_path)} - {e}.")
            else:
                print(f"Was not able to save the config to {str(self.cfg_path)} - {e}.")

    def log_pickler(self) -> None:
        """Pickle and unpickle kill logs."""
        while self.program_state["enabled"]:
            try:
                if len(self.cfg_dict["pickle"]) > 0:
                    if self.log:
                        self.log.debug(f'Current buffer: {self.cfg_dict["pickle"]}.')
                    self.save_cfg("pickle", self.cfg_dict["pickle"])
                    if self.api and getattr(self.api, "connection_healthy", False):
                        pickle_payload = self.cfg_dict["pickle"][0]
                        if self.log:
                            self.log.info(f'Attempting to post a previous kill from the buffer: {pickle_payload["kill_result"]}')
                        uploaded = self.api.post_kill_event(pickle_payload["kill_result"], pickle_payload["endpoint"])
                        if uploaded:
                            self.cfg_dict["pickle"].pop(0)
                            self.save_cfg("pickle", self.cfg_dict["pickle"])
            except Exception as e:
                if self.log:
                    self.log.error(f"log_pickler(): Error: {e.__class__.__name__} {e}")
                else:
                    print(f"log_pickler(): Error: {e.__class__.__name__} {e}")
            for sec in range(60):
                if not self.program_state["enabled"]:
                    if self.log:
                        self.log.info("Executing final config save.")
                    self.save_cfg("pickle", self.cfg_dict["pickle"])
                    break
                sleep(1)
