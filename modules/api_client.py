import requests
import webbrowser
from threading import Thread
from datetime import datetime
from packaging import version

class API_Client():
    """API client for the Kill Tracker."""
    def __init__(self, logger, gui, local_version, rsi_handle, update_queue):
        self.log = logger
        self.gui = gui
        self.local_version = local_version
        self.rsi_handle = rsi_handle
        self.update_queue = update_queue
        self.heartbeat_interval = 5
        self.request_timeout = 12
        self.api_key = {"value": None}
        self.api_key_filename = "killtracker_key.cfg"
        self.api_fqdn = "http://drawmyoshi.com:25966"


#########################################################################################################
### UPDATE API                                                                                        ###
#########################################################################################################


    def check_for_kt_updates(self) -> str:
        """Check for updates using the GitHub API."""
        try:
            github_api_url = "https://api.github.com/repos/BlightVeil/Killtracker/releases/latest"
            headers = {'User-Agent': f'Killtracker/{self.local_version}'}
            response = requests.get(
                github_api_url, 
                headers=headers, 
                timeout=self.request_timeout
            )
            if response.status_code == 200:
                release_data = response.json()
                #FIXME ?? This doesn't make sense in terms of version get, it used to be hardcoded to 1.3
                remote_version = release_data.get("tag_name", f"v{self.local_version}").strip("v") 
                download_url = release_data.get("html_url", "")

                if version.parse(self.local_version) < version.parse(remote_version):
                    return f"Update available: {remote_version}. Download it here: {download_url}"
                return ""
            else:
                self.log.error(f"GitHub API error: {response.status_code}")
                return ""
        except Exception as e:
            self.log.error(f"check_for_kt_updates(): Error checking for updates: {e.__class__.__name__} {e}")
            return ""
        
    def open_github(self, update_message:str) -> None:
        """Open a browser window to GitHub."""
        try:
            url = update_message.split("Download it here: ")[-1]
            webbrowser.open(url)
        except Exception as e:
            self.log.error(f"Error opening GitHub link: {e.__class__.__name__} {e}")


#########################################################################################################
### KEY API                                                                                           ###
#########################################################################################################


    def validate_api_key(self) -> bool:
        """Validate the API key."""
        try:
            url = f"{self.api_fqdn}/validateKey"
            headers = {
                "Authorization": self.api_key,
                "Content-Type": "application/json"
            }
            api_key_data = {
                "api_key": self.api_key,
                "player_name": self.rsi_handle["current"]
            }
            response = requests.post(
                url, 
                headers=headers, 
                json=api_key_data, 
                timeout=self.request_timeout
            )
            if response.status_code != 200:
                self.log.error(f"Error in validating the API key: code {response.status_code}")
                return False
            return True
        except requests.RequestException as e:
            self.log.error(f"validate_api_key(): Error: {e.__class__.__name__} {e}")
            return False
        
    def load_api_key(self) -> None:
        """Load the API key."""
        with open(self.api_key_filename, "r") as f:
            entered_key = f.readline().strip()
            if entered_key:
                self.api_key["value"] = entered_key
                self.log.success(f"Saved key loaded: {entered_key}. Attempting to establish Servitor connection...")
            else:
                self.api_key["value"] = None
                self.log.error("No saved key found in file. Please get a new key from the key generator.")
                self.gui.api_status_label.config(text="API Status: Invalid", fg="red")
    
    def save_api_key(self, key:str) -> None:
        """Save the API key."""
        with open(self.api_key_filename, "w") as f:
            f.write(key)
        self.api_key["value"] = key
        self.log.success(f"save_api_key(): API key saved successfully: {key}")

    def load_activate_key(self) -> None:
        """Activate and load the API key."""
        try:
            entered_key = self.gui.key_entry.get().strip()  # Access key_entry in GUI here
        except Exception as e:
            self.log.error(f"load_activate_key(): Error parsing API key: {e.__class__.__name__} {e}")
        try:
            if not entered_key:
                self.load_api_key()
        except FileNotFoundError:
            self.log.error("No saved key found. Please enter a valid key.")
            self.gui.api_status_label.config(text="API Status: Invalid", fg="red")  # Access api_status_label in GUI here
            return
        try:
            # Proceed with activation
                if self.rsi_handle["current"] != "N/A":
                    if self.validate_api_key(entered_key):
                        self.save_api_key(entered_key)  # Save the key for future use
                        self.log.success("Key activated and saved. Servitor connection established.")
                        self.log.success("Go Forth And Slaughter...")
                        self.gui.api_status_label.config(text="API Status: Valid (Expires in 72 hours)", fg="green")
                        self.start_api_key_countdown(entered_key)
                    else:
                        self.log.error("Error: Invalid API key. Please enter a valid API key.")
                        self.api_key["value"] = None
                        self.gui.api_status_label.config(text="API Status: Invalid", fg="red")
                else:
                    self.log.error("Error: Invalid RSI handle name.")
                    self.gui.api_status_label.config(text="API Status: Invalid", fg="red")
        except Exception as e:
            self.log.error(f"Error activating API key: {e.__class__.__name__} {e}")

    def post_api_key_expiration_time(self):
        """Retrieve the expiration time for the API key from the validation server."""
        try:
            if not self.api_key["value"]:
                self.log.error("Error: death event will not be sent because the API key does not exist.")
                return
            
            url = f"{self.api_fqdn}/validateKey"
            headers = {
                "Authorization": self.api_key,
                "Content-Type": "application/json"
            }
            api_key_exp_time = {
                "player_name": self.rsi_handle["current"]
            }
            response = requests.post(
                url, 
                headers=headers, 
                json=api_key_exp_time, 
                timeout=self.request_timeout
            )
            if response.status_code == 200:
                response_data = response.json()
                expiration_time_str = response_data.get("expires_at")
                if expiration_time_str:
                    return datetime.strptime(expiration_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                else:
                    raise Exception("API key expiration time not sent in Servitor response.")
            else:
                self.log.error(f"Error in posting API key expiration time: code {response.status_code}")
        except requests.exceptions.RequestException as e:
            #self.gui.async_loading_animation()
            self.log.error(f"HTTP Error sending API key expiration time event: {e}")
            self.log.error(f"Error: API key expiration time will not be sent!")
        except Exception as e:
            self.log.error(f"post_api_key_expiration_time(): Error: {e.__class__.__name__} {e}")
        # Fallback: Expire immediately if there's an error
        return None

    # FIXME THIS WHOLE FUNCTION NEEDS A REFACTOR, IT'S GIVING ME AN ANEURYSM - Samurai
    def start_api_key_countdown(self) -> None:
        """Start the countdown for the API key's expiration, refreshing expiry data periodically."""
        def countdown():
            """Calculate the remaining time."""
            remaining_time = expiration_time - datetime.datetime.utcnow()
            if remaining_time.total_seconds() > 0:
                hours, remainder = divmod(remaining_time.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                countdown_text = f"API Status: Valid (Expires in {remaining_time.days}d {hours}h {minutes}m {seconds}s)"
                self.gui.api_status_label.config(text=countdown_text, fg="green")
                self.gui.api_status_label.after(1000, countdown)  # Update every second
            else:
                self.gui.api_status_label.config(text="API Status: Expired", fg="red")

        def fetch_expiration_time():
            """Fetch expiration time in a separate thread and update countdown."""
            thread = Thread(target=threaded_request)
            thread.daemon = True
            thread.start()

        def threaded_request():
            """Get the expiration time."""
            expiration_time = self.post_api_key_expiration_time(self.api_key)  # Fetch latest expiration time
            if not expiration_time:
                self.gui.api_status_label.config(text="API Status: Expired", fg="red")
                return

            countdown()

            # Refresh expiration time every 60 seconds in a new thread
            self.gui.api_status_label.after(60000, fetch_expiration_time)

        expiration_time = None
        fetch_expiration_time()  # Initial call


#########################################################################################################
### LOG PARSER API                                                                                    ###
#########################################################################################################


    def post_kill_event(self, kill_result:dict) -> None:
        """Post the kill parsed from the log."""
        try:
            if not self.api_key["value"]:
                self.log.error("Error: kill event will not be sent because the API key does not exist. Please enter a valid API key to establish connection with Servitor...")
                return
            
            url = f"{self.api_fqdn}/reportKill"
            headers = {
                'content-type': 'application/json',
                'Authorization': self.api_key["value"] if self.api_key["value"] else ""
            }
            response = requests.post(
                url, 
                headers=headers, 
                json=kill_result["data"], 
                timeout=self.request_timeout
            )
            if response.status_code != 200:
                self.log.error(f"Error when posting kill: code {response.status_code}")
                self.log.error(f"Error: kill event {kill_result} will not be sent!")
        except requests.exceptions.RequestException as e:
            self.gui.async_loading_animation()
            self.log.error(f"HTTP Error sending kill event: {e}")
            self.log.error(f"Error: kill event {kill_result} will not be sent!")
        except Exception as e:
            self.log.error(f"post_kill_event(): Error: {e.__class__.__name__} {e}")
