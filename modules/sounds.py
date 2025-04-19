
self.global sounds_pyinst_dir
        self.global sounds_live_dir

def create_sounds_dir(logger) -> None:
    """Create directory for sounds and set vars."""
    global sounds_pyinst_dir
    global sounds_live_dir
    try:
        sounds_pyinst_dir = Path(resource_path("sounds"))  # The PyInstaller temp executable directory
        sounds_live_dir = Path.cwd() / "sounds"  # The directory where the executable lives
        # Ensure the folders exist
        sounds_pyinst_dir.mkdir(exist_ok=True)
        sounds_live_dir.mkdir(exist_ok=True)
    except Exception as e:
        logger.log(f"❌ Error when handling the sound folder: {e.__class__.__name__} {e}")


def copy_sounds(source, target, logger) -> bool:
    """Copy any new sound files from one folder to another."""
    try:
        if not source.exists():
            raise Exception(f"Source sounds folder not found: {str(source)}")
        if not target.exists():
            raise Exception(f"Target sounds folder not found: {str(target)}")
    except Exception as e:
        logger.log(f"❌ Error copying new sounds: {e.__class__.__name__} {e}")
        return False

    try:
        # Get the list of existing files in the source folder
        source_files = list(source.glob('**/*.wav'))
        logger.log(f"Found source files {source_files}")
        for sound_file in source_files:
            target_path = target / sound_file
            # Check if targets doesn't exist
            if not target_path.exists():
                shutil.copy(sound_file, target_path)
                logger.log(f"Copied sound: {sound_file} to {target_path}")
        return True
    except Exception as e:
        logger.log(f"❌ Error copying sounds: {e.__class__.__name__} {e}")
        return False

def play_random_sound(logger):
    """Play a single random .wav file from the sounds folder."""
    global sounds_live_dir
    sounds = list(sounds_live_dir.glob('**/*.wav'))
    if sounds:
        sound_to_play = random.choice(sounds)  # Select a random sound
        try:
            logger.log(f"Playing sound: {sound_to_play.name}")
            winsound.PlaySound(str(sound_to_play), winsound.SND_FILENAME | winsound.SND_ASYNC)  # Play the selected sound
            time.sleep(1)
        except Exception as e:
            logger.log(f"❌ Error playing sound {sound_to_play}: {e.__class__.__name__} {e}")
    else:
        logger.log("❌ No .wav sound files found.")
