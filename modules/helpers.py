from os import path
from sys import _MEIPASS

def resource_path(relative_path):
    """Get the absolute path to the resource (works for PyInstaller .exe and Nuitka .exe)."""
    try:
        # When running in a frozen environment (compiled executable)
        base_path = _MEIPASS  
    except AttributeError:
        # When running in a normal Python environment (source code)
        base_path = path.abspath(".")
    try:
        return path.join(base_path, relative_path)
    except Exception as e:
        print(f"❌ Error getting the absolute path to the resource path: {e.__class__.__name__} {e}")
        return relative_path

def get_sc_log_path(directory, logger):
    """Search for Game.log in the directory and its parent directory."""
    game_log_path = path.join(directory, 'Game.log')
    if path.exists(game_log_path):
        logger.log(f"Found Game.log in: {directory}")
        return game_log_path
    # If not found in the same directory, check the parent directory
    parent_directory = path.dirname(directory)
    game_log_path = path.join(parent_directory, 'Game.log')
    if path.exists(game_log_path):
        logger.log(f"Found Game.log in parent directory: {parent_directory}")
        return game_log_path
    return None

def get_sc_log_location(logger):
    """Check for RSI Launcher and Star Citizen Launcher, and get the log path."""
    # Check if RSI Launcher is running
    rsi_launcher_path = check_if_process_running("RSI Launcher")
    if not rsi_launcher_path:
        logger.log("⚠️ RSI Launcher not running.")
        return None

    logger.log(f"✅ RSI Launcher running at: {rsi_launcher_path}")

    # Check if Star Citizen Launcher is running
    sc_launcher_path = check_if_process_running("StarCitizen")
    if not sc_launcher_path:
        logger.log("⚠️ Star Citizen Launcher not running.")
        return None
    
    logger.log(f"✅ Star Citizen Launcher running at: {sc_launcher_path}")

    # Search for Game.log in the folder next to StarCitizen_Launcher.exe
    star_citizen_dir = path.dirname(sc_launcher_path)
    logger.log(f"Searching for Game.log in directory: {star_citizen_dir}")
    log_path = get_sc_log_path(star_citizen_dir, logger)

    if log_path:
        return log_path
    else:
        logger.log("⚠️ Game.log not found in expected locations.")
        return None