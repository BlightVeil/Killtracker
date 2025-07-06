from time import sleep
from random import choice
from os import listdir, path
from pathlib import Path
import shutil
import pygame
pygame.mixer.init()

# Import kill tracker modules
import modules.helpers as Helpers

class Sounds():
    """Sounds module for the Kill Tracker."""
    def __init__(self):
        self.log = None
        self.sounds_pyinst_dir = None
        self.sounds_live_dir = None
        self.volume = 0.5  # Default volume (0.0 to 1.0)

    def set_volume(self, volume):
        """Set the playback volume."""
        self.volume = volume
        pygame.mixer.music.set_volume(self.volume)
        if self.log:
            self.log.info(f"Sound volume set to {self.volume * 100:.0f}%")

    def setup_sounds(self) -> None:
        """Setup the sounds module."""
        try:
            self.create_sounds_dir()
            self.copy_sounds(self.sounds_pyinst_dir, self.sounds_live_dir)

            # ✅ Always show logs
            sound_files = listdir(str(self.sounds_live_dir)) if path.exists(str(self.sounds_live_dir)) else []
            if self.log:
                self.log.info(f"Included sounds found at: {str(self.sounds_live_dir)}")
                self.log.info(f"Sound Files inside: {sound_files}")
                self.log.success("✅ To add new Sounds to the Kill Tracker, drop in .wav files to the sounds folder.")
        except Exception as e:
            if self.log:
                self.log.error(f"setup_sounds(): Error: {e.__class__.__name__} {e}")

    def create_sounds_dir(self) -> None:
        """Create directory for sounds and set vars."""
        try:
            self.sounds_pyinst_dir = Path(Helpers.resource_path("static/sounds"))
            self.sounds_live_dir = Path.cwd() / "sounds"
            self.sounds_pyinst_dir.mkdir(exist_ok=True)
            self.sounds_live_dir.mkdir(exist_ok=True)
            if self.log:
                self.log.debug(f"PyInstaller temp executable directory: {str(self.sounds_pyinst_dir)}")
                self.log.debug(f"The directory where the executable lives: {str(self.sounds_live_dir)}")
        except Exception as e:
            if self.log:
                self.log.error(f"create_sounds_dir(): Error: {e.__class__.__name__} {e}")

    def copy_sounds(self, source, target) -> None:
        """Copy new sound files from one folder to another."""
        try:
            if not source.exists():
                raise Exception(f"Source sounds folder not found: {str(source)}")
            if not target.exists():
                raise Exception(f"Target sounds folder not found: {str(target)}")
        except Exception as e:
            if self.log:
                self.log.error(f"copy_sounds(): {e.__class__.__name__} {e}")
            return

        try:
            source_files = list(source.glob('**/*.wav'))
            for sound_file in source_files:
                target_path = target / sound_file.name
                if not target_path.exists():
                    shutil.copy(sound_file, target_path)
                    if self.log:
                        self.log.debug(f"Copied sound: {sound_file} to {target_path}")
        except Exception as e:
            if self.log:
                self.log.error(f"Error copying sounds: {e.__class__.__name__} {e}")

    def play_random_sound(self):
        """Play a random sound from the sounds folder."""
        sounds = list(self.sounds_live_dir.glob('**/*.wav')) if self.sounds_live_dir else []
        if sounds:
            sound_to_play = choice(sounds)
            try:
                if self.log:
                    self.log.debug(f"Playing sound: {sound_to_play.name}")
                sound = pygame.mixer.Sound(str(sound_to_play))
                sound.set_volume(self.volume)
                sound.play()
                sleep(sound.get_length())
            except Exception as e:
                if self.log:
                    self.log.error(f"Error playing sound {sound_to_play}: {e.__class__.__name__} {e}")
        else:
            if self.log:
                self.log.error("No .wav sound files found.")
