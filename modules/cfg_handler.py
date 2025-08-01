import base64
import hashlib
import json
import re
from time import sleep
from pathlib import Path

class Cfg_Handler:
    """Config Handler with backward compatibility and per-account encrypted config."""

    def __init__(self, program_state, monitoring, rsi_handle):
        self.log = None
        self.gui = None
        self.api = None
        self.program_state = program_state
        self.monitoring = monitoring
        self.rsi_handle = rsi_handle
        self.old_cfg_path = Path.cwd() / "bv_killtracker.cfg"
        self.crypt_key = None
        self.cfg_path = None
        self.cfg_dict = {"key": "", "volume": {"level": 0.5, "is_muted": False}, "pickle": []}

    def _safe_filename(self) -> str:
        return re.sub(r'[\\/*?:"<>|]', "_", self.rsi_handle["current"])

    def _derive_key(self) -> bytes:
        """Derive a 32-byte key from the RSI handle using SHA256."""
        return hashlib.sha256(self.rsi_handle["current"].encode()).digest()

    def _xor_encrypt(self, data: bytes) -> bytes:
        """Simple XOR encrypt/decrypt with repeating key."""
        return bytes(b ^ self.crypt_key[i % len(self.crypt_key)] for i, b in enumerate(data))

    def _set_cfg_vars(self):
        if self.rsi_handle["current"] == "N/A":
            self.log.error("Tried setting the RSI handle but it does not exist.")
            return
        self.crypt_key = self._derive_key()
        self.cfg_path = Path.cwd() / f'bv_killtracker_{self._safe_filename()}.cfg'
        self.log.debug(f"Set config file path: {self.cfg_path}")

    def migrate_old_configs(self):
        # Migrate old config file
        try:
            if self.old_cfg_path.exists() and self.cfg_path and not self.cfg_path.exists():
                self.log.info(f"Found old v1.6 config file: {self.old_cfg_path}")
                # Read v1.6 base64-encoded JSON config
                with open(self.old_cfg_path, "r") as f:
                    base64_data = f.readline().strip()
                json_str = base64.b64decode(base64_data.encode('ascii')).decode('ascii')
                self.cfg_dict = json.loads(json_str)
                self.log.debug(f"Loaded old v1.6 config file: {self.cfg_dict}")
                # Requires RSI handle to be set
                self.save_cfg("all", "")
                self.old_cfg_path.unlink()
                self.log.debug(f"Migrated and removed old v1.6 config file.")
        except Exception as e:
            self.log.error(f"Failed to migrate old v1.6 config: {e.__class__.__name__} {e}")

    def load_cfg(self, data_type: str):
        """Load the config with simple XOR decryption."""
        if not self.cfg_path or not self.crypt_key:
            self.log.error("Cannot load config: RSI handle not set.")
            return "error"

        if not self.cfg_path.exists():
            if self.log:
                self.log.debug(f"Config file {self.cfg_path} not found. Using default config.")
            else:
                print(f"Config file {self.cfg_path} not found. Using default config.")
            return self.cfg_dict.get(data_type, "error")

        try:
            with open(str(self.cfg_path), "rb") as f:
                file_data = f.readline().strip()
            # Try XOR decrypt + base64 decode
            try:
                decrypted_data = self._xor_encrypt(base64.b64decode(file_data)).decode()
                self.cfg_dict = json.loads(decrypted_data)
                if self.log:
                    self.log.debug(f"load_cfg(): cfg: {self.cfg_dict}")
                else:
                    print(f"load_cfg(): cfg: {self.cfg_dict}")

                if data_type == "volume":
                    self.gui.volume_slider.set(self.cfg_dict["volume"]["level"] * 100)
                    if self.cfg_dict["volume"]["is_muted"]:
                        self.gui.mute_button.config(text="🔇", fg="#ffffff", bg="#8A0000")
                
                return self.cfg_dict.get(data_type, "error")
            except Exception as e:
                if self.log:
                    self.log.error(f"Failed to load config file: {e.__class__.__name__} {e}")
                else:
                    print(f"Failed to load config file: {e.__class__.__name__} {e}")
                self.log.debug("Trying fallback decode.")
                # Fallback: old Base64 encoded JSON (should not happen if migrated)
                cfg_str = base64.b64decode(file_data).decode()
                self.cfg_dict = json.loads(cfg_str)
                if self.log:
                    self.log.warning("Fallback: loaded old Base64 config.")
                else:
                    print("Fallback: loaded old Base64 config.")
                return self.cfg_dict.get(data_type, "error")
        except Exception as e:
            if self.log:
                self.log.error(f"Failed to load config file: {e.__class__.__name__} {e}")
            else:
                print(f"Failed to load config file: {e.__class__.__name__} {e}")
            return "error"

    def save_cfg(self, data_type: str, data) -> None:
        """Encrypt and save the configuration with XOR and base64."""
        if not self.cfg_path or not self.crypt_key:
            self.log.error("Cannot save config: RSI handle not set.")
            return
        try:
            if data_type != "all":
                self.cfg_dict[data_type] = data
            cfg_json = json.dumps(self.cfg_dict)
            encrypted_data = base64.b64encode(self._xor_encrypt(cfg_json.encode()))
            with open(str(self.cfg_path), "wb") as f:
                f.write(encrypted_data)
            self.log.debug(f"Successfully saved encrypted config to {str(self.cfg_path)}")
        except Exception as e:
            self.log.error(f"Was not able to save the config to {str(self.cfg_path)} - {e.__class__.__name__} {e}.")

    def log_pickler(self) -> None:
        """Pickle and unpickle kill logs."""
        while self.program_state["enabled"]:
            try:
                if self.log:
                    self.log.debug(f'Current pickling buffer: {self.cfg_dict["pickle"]}')
                
                if self.monitoring["active"] and len(self.cfg_dict["pickle"]) > 0:
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
                self.log.error(f"log_pickler(): {e.__class__.__name__} {e}")

            for sec in range(60):
                if not self.program_state["enabled"]:
                    if self.log:
                        self.log.info("Executing final config save.")
                    self.save_cfg("pickle", self.cfg_dict["pickle"])
                    break
                sleep(1)
