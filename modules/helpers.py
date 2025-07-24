from os import path
import sys

def resource_path(relative_path:str) -> str:
    """Get the absolute path to the resource (works for PyInstaller .exe and Nuitka .exe)."""
    try:
        # When running in a frozen environment (compiled executable)
        base_path = sys._MEIPASS  
    except AttributeError:
        # When running in a normal Python environment (source code)
        base_path = path.abspath(".")
    try:
        return path.join(base_path, relative_path)
    except Exception:
        return relative_path
