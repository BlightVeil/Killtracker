from time import sleep
from random import choice
from os import listdir, path
from pathlib import Path
import shutil
import pygame

# Import kill tracker modules
import modules.helpers as Helpers

class Sounds():
    """Sounds module for the Kill Tracker."""
    def __init__(self, cfg_handler, mute_state):
        self.log = None
        self.cfg_handler = cfg_handler
        self.mute_state = mute_state
        self.sounds_pyinst_dir = None
        self.sounds_live_dir = None
        self.curr_volume = 0.5  # Default volume (0.0 to 1.0)
        self.prev_volume = 0.5
        pygame.mixer.init()

    def load_sound_settings(self) -> None:
        """Load sound settings from cfg."""
        try:
            volume_dict = self.cfg_handler.cfg_dict["volume"]
            self.mute_state["enabled"] = volume_dict["is_muted"]
            self.prev_volume = volume_dict["level"]
            self.curr_volume = 0.0 if self.mute_state["enabled"] else self.prev_volume

            if self.mute_state["enabled"]:
                if self.log:
                    self.log.info("Sound volume muted.")
                else:
                    print("Sound volume muted.")
            else:
                if self.log:
                    self.log.info(f"Sound volume set to {self.curr_volume * 100:.0f}%")
                else:
                    print(f"Sound volume set to {self.curr_volume * 100:.0f}%")
        except Exception as e:
            if self.log:
                self.log.warning(f"load_sound_settings(): {e.__class__.__name__} {e}")
            else:
                print(f"load_sound_settings(): {e.__class__.__name__} {e}")

    def set_volume(self, volume:float) -> None:
        """Set the playback volume."""
        try:
            if volume != -1.0:
                # Handle flags, not volume
                self.curr_volume = volume
                self.prev_volume = volume
            if self.mute_state["enabled"]:
                self.curr_volume = 0.0
                self.log.info(f"Sound volume muted.")
            else:
                if self.curr_volume != self.prev_volume:
                    self.log.info(f"Sound volume unmuted.")
                self.curr_volume = self.prev_volume

            pygame.mixer.music.set_volume(self.curr_volume)

            self.cfg_handler.cfg_dict["volume"]["level"] = self.prev_volume
            self.cfg_handler.cfg_dict["volume"]["is_muted"] = self.mute_state["enabled"]

            if not self.mute_state["enabled"]:
                self.log.debug(f"Sound volume set to {self.curr_volume * 100:.0f}%")
        except Exception as e:
            self.log.error(f"set_volume(): {e.__class__.__name__} {e}")

    def setup_sounds(self) -> None:
        """Setup the sounds module."""
        try:
            self.create_sounds_dir()
            self.copy_sounds(self.sounds_pyinst_dir, self.sounds_live_dir)

            # ✅ Always show logs
            sound_files = listdir(str(self.sounds_live_dir)) if path.exists(str(self.sounds_live_dir)) else []
            self.log.info(f"Included sounds found at: {str(self.sounds_live_dir)}")
            self.log.info(f"Sound Files inside: {sound_files}")
            self.log.info("To add new Sounds to the Kill Tracker, drop in .wav files to the sounds folder.")
        except Exception as e:
            self.log.error(f"setup_sounds(): {e.__class__.__name__} {e}")

    def create_sounds_dir(self) -> None:
        """Create directory for sounds and set vars."""
        try:
            self.sounds_pyinst_dir = Path(Helpers.resource_path("static/sounds"))
            self.sounds_live_dir = Path.cwd() / "sounds"
            self.sounds_pyinst_dir.mkdir(exist_ok=True)
            self.sounds_live_dir.mkdir(exist_ok=True)
            self.log.debug(f"PyInstaller temp executable directory: {str(self.sounds_pyinst_dir)}")
            self.log.debug(f"The directory where the executable lives: {str(self.sounds_live_dir)}")
        except Exception as e:
            self.log.error(f"create_sounds_dir(): {e.__class__.__name__} {e}")

    def copy_sounds(self, source:Path, target:Path) -> None:
        """Copy new sound files from one folder to another."""
        try:
            if not source.exists():
                raise Exception(f"Source sounds folder not found: {str(source)}")
            if not target.exists():
                raise Exception(f"Target sounds folder not found: {str(target)}")
        except Exception as e:
            self.log.error(f"copy_sounds(): {e.__class__.__name__} {e}")

        try:
            source_files = list(source.glob('**/*.wav'))
            for sound_file in source_files:
                target_path = target / sound_file.name
                if not target_path.exists():
                    shutil.copy(sound_file, target_path)
                    self.log.debug(f"Copied sound: {sound_file} to {target_path}")
        except Exception as e:
            self.log.error(f"copy_sounds(): {e.__class__.__name__} {e}")

    def play_random_sound(self) -> None:
        """Play a random sound from the sounds folder."""
        sounds = list(self.sounds_live_dir.glob('**/*.wav')) if self.sounds_live_dir else []
        if sounds:
            sound_to_play = choice(sounds)
            try:
                self.log.debug(f"Playing sound: {sound_to_play.name}")
                sound = pygame.mixer.Sound(str(sound_to_play))
                sound.set_volume(self.curr_volume)
                sound.play()
                sleep(sound.get_length())
            except Exception as e:
                self.log.error(f"When playing sound {sound_to_play}: {e.__class__.__name__} {e}")
        else:
            self.log.error("No sound files found.")
