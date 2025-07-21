import base64
import hashlib
import json
import re
import time
from time import sleep
from pathlib import Path

class Cfg_Handler:
    """Config Handler with backward compatibility and per-account encrypted config."""

    def __init__(self, program_state, rsi_handle=None):
        self.log = None
        self.api = None
        self.program_state = program_state
        self.old_key_path = Path.cwd() / "killtracker_key.cfg"
        self.old_cfg_path = Path.cwd() / "bv_killtracker.cfg"

        self.rsi_handle = rsi_handle if rsi_handle and rsi_handle != "N/A" else None
        self.cfg_dict = {"key": "", "volume": {"level": 0.5, "is_muted": False}, "pickle": []}
        self.key = None
        self.cfg_path = None

        if self.rsi_handle:
            self._set_handle(self.rsi_handle)

    def _safe_filename(self, handle: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "_", handle)

    def _derive_key(self, rsi_handle: str) -> bytes:
        return hashlib.sha256(rsi_handle.encode()).digest()

    def _xor_encrypt(self, data: bytes) -> bytes:
        return bytes(b ^ self.key[i % len(self.key)] for i, b in enumerate(data))

    def _set_handle(self, handle: str):
        self.rsi_handle = handle
        self.key = self._derive_key(handle)
        self.cfg_path = Path.cwd() / f"bv_killtracker_{self._safe_filename(handle)}.cfg"
        print(f"Using config file: {self.cfg_path}")

    def wait_for_rsi_handle(self, find_handle_callback, timeout=30, interval=2):
        start_time = time.time()
        while (not self.rsi_handle or self.rsi_handle == "N/A") and (time.time() - start_time < timeout):
            handle = find_handle_callback()
            if handle and handle != "N/A":
                self._set_handle(handle)
                self.load_cfg("pickle")
                return True
            time.sleep(interval)
        if not self.rsi_handle or self.rsi_handle == "N/A":
            print("RSI handle not found within timeout.")
            return False
        return True

    def update_rsi_handle(self, new_handle: str):
        if not new_handle or new_handle == "N/A":
            return
        if new_handle != self.rsi_handle:
            self._set_handle(new_handle)
            self.cfg_dict = {"key": "", "volume": {"level": 0.5, "is_muted": False}, "pickle": []}
            print(f"Switched to new RSI handle: {self.rsi_handle}")
            self.load_cfg("pickle")

    def migrate_old_configs(self):
        # Migrate old key file
        if self.old_key_path.exists() and (not self.cfg_path or not self.cfg_path.exists()):
            try:
                with open(self.old_key_path, "r") as f:
                    old_key = f.readline().strip()
                if old_key:
                    print(f"Kill Tracker v1.5 saved key loaded: {old_key}")
                    self.cfg_dict["key"] = old_key
                    self.save_cfg("key", old_key)
                self.old_key_path.unlink()
                print("Migrated and removed old Kill Tracker key file.")
            except Exception as e:
                print(f"Failed to migrate old key file: {e}")

        # Migrate old config file
        if self.old_cfg_path.exists() and self.cfg_path and not self.cfg_path.exists():
            try:
                # Read old base64-encoded JSON config
                with open(self.old_cfg_path, "r") as f:
                    base64_data = f.readline().strip()
                json_str = base64.b64decode(base64_data.encode('ascii')).decode('ascii')
                self.cfg_dict = json.loads(json_str)
                print(f"Migrated old config loaded: {self.cfg_dict}")
                self.save_cfg("pickle", self.cfg_dict.get("pickle", []))
                self.old_cfg_path.unlink()
                print(f"Migrated and removed old config file to {self.cfg_path}")
            except Exception as e:
                print(f"Failed to migrate old config file: {e}")

    def load_cfg(self, data_type: str):
        if not self.cfg_path or not self.key:
            print("Cannot load config: RSI handle not set.")
            return "error"

        # Run migrations if needed
        self.migrate_old_configs()

        if not self.cfg_path.exists():
            print(f"Config file {self.cfg_path} not found. Using default config.")
            return self.cfg_dict.get(data_type, "error")

        try:
            with open(str(self.cfg_path), "rb") as f:
                file_data = f.read()
            # Try XOR decrypt + base64 decode
            try:
                decrypted_data = self._xor_encrypt(base64.b64decode(file_data)).decode('utf-8')
                self.cfg_dict = json.loads(decrypted_data)
                print(f"load_cfg(): cfg: {self.cfg_dict}")
                return self.cfg_dict.get(data_type, "error")
            except Exception:
                # Fallback: old Base64 encoded JSON (should not happen if migrated)
                cfg_str = base64.b64decode(file_data).decode('ascii')
                self.cfg_dict = json.loads(cfg_str)
                print("Fallback: loaded old Base64 config.")
                return self.cfg_dict.get(data_type, "error")
        except Exception as e:
            print(f"Failed to load config file: {e}")
            return "error"

    def save_cfg(self, data_type: str, data) -> None:
        if not self.cfg_path or not self.key:
            print("Cannot save config: RSI handle not set.")
            return
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
