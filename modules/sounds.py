from time import sleep
from random import choice
from os import listdir, path
from pathlib import Path
import shutil
import winsound

# Import kill tracker modules
import modules.helpers as Helpers

class Sounds():
    """Sounds module for the Kill Tracker."""
    def __init__(self):
        self.log = None
        self.sounds_pyinst_dir = None
        self.sounds_live_dir = None

    def setup_sounds(self) -> None:
        """Setup the sounds module."""
        try:
            self.create_sounds_dir()
            copy_to_user_dir = self.copy_sounds(self.sounds_pyinst_dir, self.sounds_live_dir)
            if copy_to_user_dir:
                self.log.info(f"Included sounds found at: {str(self.sounds_live_dir)}")
                self.log.info(f"Sound Files inside: {listdir(str(self.sounds_live_dir)) if path.exists(str(self.sounds_live_dir)) else 'Not Found'}")
                self.log.success("To add new Sounds to the Kill Tracker, drop in .wav files to the sounds folder.")
        except Exception as e:
            self.log.error(f"setup_sounds(): Error: {e.__class__.__name__} {e}")

    def create_sounds_dir(self) -> None:
        """Create directory for sounds and set vars."""
        try:
            self.sounds_pyinst_dir = Path(Helpers.resource_path("sounds"))  # The PyInstaller temp executable directory
            self.sounds_live_dir = Path.cwd() / "sounds"  # The directory where the executable lives
            # Ensure the folders exist
            self.sounds_pyinst_dir.mkdir(exist_ok=True)
            self.sounds_live_dir.mkdir(exist_ok=True)
        except Exception as e:
            self.log.error(f"create_sounds_dir(): Error: {e.__class__.__name__} {e}")

    def copy_sounds(self, source, target) -> bool:
        """Copy any new sound files from one folder to another."""
        try:
            if not source.exists():
                raise Exception(f"Source sounds folder not found: {str(source)}")
            if not target.exists():
                raise Exception(f"Target sounds folder not found: {str(target)}")
        except Exception as e:
            self.log.error(f"copy_sounds(): {e.__class__.__name__} {e}")
            return False

        try:
            # Get the list of existing files in the source folder
            source_files = list(source.glob('**/*.wav'))
            self.log.info(f"Found source files {source_files}")
            for sound_file in source_files:
                target_path = target / sound_file
                # Check if targets doesn't exist
                if not target_path.exists():
                    shutil.copy(sound_file, target_path)
                    self.log.info(f"Copied sound: {sound_file} to {target_path}")
            return True
        except Exception as e:
            self.log.error(f"Error copying sounds: {e.__class__.__name__} {e}")
            return False

    def play_random_sound(self):
        """Play a single random .wav file from the sounds folder."""
        sounds = list(self.sounds_live_dir.glob('**/*.wav'))
        if sounds:
            sound_to_play = choice(sounds)  # Select a random sound
            try:
                self.log(f"Playing sound: {sound_to_play.name}")
                winsound.PlaySound(str(sound_to_play), winsound.SND_FILENAME | winsound.SND_ASYNC)  # Play the selected sound
                sleep(1)
            except Exception as e:
                self.log.error(f"Error playing sound {sound_to_play}: {e.__class__.__name__} {e}")
        else:
            self.log.error("No .wav sound files found.")
