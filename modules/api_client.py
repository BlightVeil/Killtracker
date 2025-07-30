import requests
import webbrowser
from threading import Thread
from datetime import datetime
import pytz
from tzlocal import get_localzone
from packaging import version
from time import sleep
import itertools

class API_Client():
    """API client for the Kill Tracker."""
    def __init__(self, cfg_handler, gui, monitoring, local_version, rsi_handle):
        self.log = None
        self.cm = None
        self.cfg_handler = cfg_handler
        self.gui = gui
        self.cfg_handler = cfg_handler
        self.monitoring = monitoring
        self.local_version = local_version
        self.rsi_handle = rsi_handle
        self.request_timeout = 60
        self.api_key = {"value": None}
        self.api_fqdn = "http://blightveil.org:25966"
        self.sc_data = {"weapons": [], "ships": [], "ignoredVictimRules": []}
        self.expiration_time = None
        self.countdown_active = False
        self.connection_healthy = False
        self.countdown_interval = 60
        self.key_status_valid_color = "#04B431"
        self.key_status_invalid_color = "red"


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
                print(f"GitHub API error: {response.status_code}")
                return ""
        except Exception as e:
            print(f"check_for_kt_updates(): Error checking for updates: {e.__class__.__name__} {e}")
            return ""
        
    def open_github(self, update_message:str) -> None:
        """Open a browser window to GitHub."""
        try:
            url = update_message.split("Download it here: ")[-1]
            webbrowser.open(url)
        except Exception as e:
            print(f"Error opening GitHub link: {e.__class__.__name__} {e}")


#########################################################################################################
### KEY API                                                                                           ###
#########################################################################################################


    def validate_api_key(self, key) -> bool:
        """Validate the API key."""
        try:
            url = f"{self.api_fqdn}/validateKey"
            headers = {
                "Authorization": key,
                "Content-Type": "application/json"
            }
            api_key_data = {
                "api_key": key,
                "player_name": self.rsi_handle["current"]
            }
            self.log.debug(f"validate_api_key(): Request payload: {api_key_data}")
            response = requests.post(
                url, 
                headers=headers, 
                json=api_key_data, 
                timeout=self.request_timeout
            )
            self.log.debug(f"validate_api_key(): Response text: {response.text}")
            if response.status_code != 200:
                self.log.error(f"Error in validating the key: code {response.status_code}")
                self.connection_healthy = False
                return False
            self.connection_healthy = True
            return True
        except requests.RequestException as e:
            self.log.error(f"validate_api_key(): Request Error: {e.__class__.__name__} {e}")
        except Exception as e:
            self.log.error(f"validate_api_key(): General Error: {e.__class__.__name__} {e}")
        self.connection_healthy = False
        return False

    def load_activate_key(self) -> None:
        """Activate and load the API key."""
        try:
            entered_key = self.gui.key_entry.get().strip()  # Access key_entry in GUI here
        except Exception as e:
            self.log.error(f"load_activate_key(): Parsing key: {e.__class__.__name__} {e}")
        try:
            if not entered_key:
                entered_key = self.cfg_handler.load_cfg("key")
            if entered_key == "error":
                self.gui.api_status_label.config(text="Key Status: Invalid", fg=self.key_status_invalid_color)
        except FileNotFoundError:
            self.log.error("No saved key found. Please enter a valid key.")
            self.gui.api_status_label.config(text="Key Status: Invalid", fg=self.key_status_invalid_color)  # Access api_status_label in GUI here
            return
        try:
            # Proceed with activation
            if self.rsi_handle["current"] != "N/A":
                if self.validate_api_key(entered_key):
                    self.cfg_handler.save_cfg("key", entered_key)
                    self.api_key["value"] = entered_key
                    self.log.success("Key activated and saved. Servitor connection established.")
                    self.gui.api_status_label.config(text="Key Status: Valid", fg=self.key_status_valid_color)
                    if not self.countdown_active:
                        self.countdown_active = True
                        thr = Thread(target=self.start_api_key_countdown, daemon=True)
                        thr.start()
                else:
                    self.log.error("Invalid key. Please enter a valid key from Discord.")
                    self.api_key["value"] = None
                    self.gui.api_status_label.config(text="Key Status: Invalid", fg=self.key_status_invalid_color)
            else:
                self.log.error("RSI handle name has not been found yet!")
                self.gui.api_status_label.config(text="Key Status: Invalid", fg=self.key_status_invalid_color)
        except Exception as e:
            self.log.error(f"Error activating key: {e.__class__.__name__} {e}")

    def post_api_key_expiration_time(self):
        """Retrieve the expiration time for the API key from the validation server."""
        try:
            url = f"{self.api_fqdn}/validateKey"
            headers = {
                "Authorization": self.api_key["value"],
                "Content-Type": "application/json"
            }
            api_key_exp_time = {
                "player_name": self.rsi_handle["current"]
            }
            self.log.debug(f"post_api_key_expiration_time(): Request payload: {api_key_exp_time}")
            response = requests.post(
                url, 
                headers=headers, 
                json=api_key_exp_time, 
                timeout=self.request_timeout
            )
            self.log.debug(f"post_api_key_expiration_time(): Response text: {response.text}")
            if response.status_code == 200:
                self.connection_healthy = True
                response_data = response.json()
                post_key_exp_result = response_data.get("expires_at")
                if post_key_exp_result:
                    return post_key_exp_result
                else:
                    self.log.error("Key expiration time not sent in Servitor response.")
            elif response.status_code == 403:
                self.connection_healthy = False
                return "invalidated"
            else:
                self.log.error(f"Error in posting key expiration time: code {response.status_code}")
        except requests.exceptions.RequestException as e:
            #self.gui.async_loading_animation()
            self.log.error(f"HTTP Error sending key expiration time event: {e}")
            self.log.error(f"Key expiration time will not be sent!")
        except Exception as e:
            self.log.error(f"post_api_key_expiration_time(): {e.__class__.__name__} {e}")
        # Fallback
        self.connection_healthy = False
        return "error"

    def start_api_key_countdown(self) -> None:
        """Start the countdown for the API key's expiration, refreshing expiry data periodically."""
        def stop_countdown():
            if self.cm:
                self.cm.stop_heartbeat_threads()
            self.api_key["value"] = None
            self.monitoring["active"] = False
            self.gui.api_status_label.config(text="Key Status: Expired", fg=self.key_status_invalid_color)
            self.countdown_active = False

        server_tz = pytz.timezone('US/Mountain')
        local_tz = get_localzone()

        while self.countdown_active:
            try:
                if not self.api_key["value"]:
                    raise Exception("Request to get the expiration time will not be sent because the API key does not exist.")
                if self.rsi_handle["current"] == "N/A":
                    self.log.debug("start_api_key_countdown(): RSI handle name does not exist. Game was closed?")
                    continue

                # Get the expiration time from the server (already returned in UTC)
                post_key_exp_result = self.post_api_key_expiration_time()
                if post_key_exp_result == "error":
                    self.log.warning("Failed to get the key expiration time. Continuing anyway ...")
                elif post_key_exp_result == "invalidated":
                    self.cfg_handler.save_cfg("key", "")
                    self.log.error("Key has been invalidated by Servitor. Please get a new key or speak with a BlightVeil admin.")
                    stop_countdown()
                    continue # Skip further calculations if invalidated
                # Expiration time was returned
                else:
                    expiration_time = datetime.strptime(post_key_exp_result, "%Y-%m-%dT%H:%M:%S.%fZ")
                    expiration_time = expiration_time.replace(tzinfo=local_tz)
                    now = datetime.now(server_tz)

                    # Check if the key has expired
                    if now > expiration_time:
                        self.log.error(f"Key expired. Please enter a new Kill Tracker key.")
                        self.cfg_handler.save_cfg("key", "")
                        stop_countdown()
                        continue # Skip further calculations if expired

                    # Calculate the remaining time
                    remaining_time = expiration_time - now
                    total_seconds = int(remaining_time.total_seconds())

                    # Debugging output
                    self.log.debug(f"Expiration Time: {expiration_time}")
                    self.log.debug(f"Current Time (now): {now}")
                    self.log.debug(f"Remaining Time: {remaining_time}")
                    self.log.debug(f"Total Seconds Remaining: {total_seconds}")

                    # Break the total seconds into days, hours, minutes, and seconds
                    days, remainder = divmod(total_seconds, 86400)
                    hours, remainder = divmod(remainder, 3600)
                    minutes, seconds = divmod(remainder, 60)

                    # Building the countdown text
                    if total_seconds > 0:
                        if days > 0:
                            countdown_text = f"Key Status: Valid (Expires in {days} days)"
                        elif hours > 0:
                            countdown_text = f"Key Status: Valid (Expires in {hours} hours {minutes} minutes)"
                        else:
                            countdown_text = f"Key Status: Valid (Expires in {minutes} minutes {seconds} seconds)"
                        self.gui.api_status_label.config(text=countdown_text, fg=self.key_status_valid_color)
                        self.cfg_handler.save_cfg("key", self.api_key["value"])
                        # Update local SC data
                        self.log.debug("Pulling SC data mappings from Servitor.")
                        self.get_data_map("weapons")
                        sleep(1)
                        #self.get_data_map("ships") # NOT NEEDED ATM
                        #sleep(1)
                        self.get_data_map("ignoredVictimRules")
                        sleep(1)
                    else:
                        self.log.error(f"Key expired. Please enter a new Kill Tracker key.")
                        self.cfg_handler.save_cfg("key", "")
                        stop_countdown()
            except Exception as e:
                self.log.error(f"General error in key expiration countdown: {e.__class__.__name__} {e}")
            finally:
                sleep(self.countdown_interval)
        
#########################################################################################################
### LOG PARSER API                                                                                    ###
#########################################################################################################

    def get_data_map(self, data_type:str) -> None:
        """Get data map from the server."""
        try:
            if not self.api_key["value"]:
                self.log.warning("Data map for {} will not be pulled because the key does not exist. Using default mappings.")
                return
            
            url = f"{self.api_fqdn}/api/server/data/{data_type}"
            headers = {
                'Authorization': self.api_key["value"] if self.api_key["value"] else ""
            }
            self.log.debug(f"get_data_map(): Requesting data for {data_type} from Servitor.")
            response = requests.get(
                url, 
                headers=headers, 
                timeout=self.request_timeout
            )
            if response.status_code == 200:
                self.connection_healthy = True
                self.log.debug(f'{data_type} data has been downloaded from Servitor.')
                # Merge incoming SC data into new dict
                server_data = response.json()[data_type]
                diff = list(itertools.filterfalse(lambda x: x in self.sc_data[data_type], server_data)) + list(itertools.filterfalse(lambda x: x in server_data, self.sc_data[data_type]))
                if len(diff) > 0:
                    self.log.debug(f"get_data_map(): Local SC data for the Kill Tracker differs from Servitor data. Updating local data for {data_type}")
                    self.log.debug(f'get_data_map(): Diff for {data_type} data: {diff}')
                    self.sc_data[data_type] = server_data
                else:
                    self.log.debug(f"get_data_map(): Local SC data for {data_type} is the same as Servitor.")
            else:
                self.log.error(f"{response.status_code} Error when pulling data for {data_type}.")
                self.connection_healthy = False
        except requests.exceptions.RequestException as e:
            self.log.error(f"HTTP Error when pulling data for {data_type}: {e}")
            self.connection_healthy = False
        except Exception as e:
            self.log.error(f"get_data_map(): {e.__class__.__name__} {e}")
            self.connection_healthy = False

    def post_kill_event(self, kill_result: dict, endpoint: str) -> bool:
        """Post the kill parsed from the log."""
        try:
            if not self.api_key["value"]:
                self.log.error("Kill event will not be sent because the key does not exist. Please enter a valid Kill Tracker key to establish connection with Servitor...")
                return
            
            url = f"{self.api_fqdn}/{endpoint}"
            headers = {
                'content-type': 'application/json',
                'Authorization': self.api_key["value"] if self.api_key["value"] else ""
            }
            self.log.debug(f"post_kill_event(): Sending to API {endpoint} the payload: {kill_result['data']}")
            response = requests.post(
                url, 
                headers=headers, 
                json=kill_result["data"], 
                timeout=self.request_timeout
            )
            self.log.debug(f"post_kill_event(): Response text: {response.text}")
            if response.status_code == 200:
                self.connection_healthy = True
                self.log.success(f'Kill of {kill_result["data"]["victim"]} by {kill_result["data"]["player"]} has been posted to Servitor!')
                return True
            else:
                self.log.error(f"Error when posting kill: code {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.gui.async_loading_animation()
            self.log.error(f"HTTP Error sending kill event: {e}")
        except Exception as e:
            self.log.error(f"post_kill_event(): {e.__class__.__name__} {e}")
        # Failure state
        self.log.error(f"Kill event will not be sent! Event dump: {kill_result}")
        self.connection_healthy = False
        pickle_payload = {"kill_result": kill_result, "endpoint": endpoint}
        if pickle_payload not in self.cfg_handler.cfg_dict["pickle"]:
            self.cfg_handler.cfg_dict["pickle"].append(pickle_payload)
            self.log.warning(f'Connection seems to be unhealthy. Pickling kill.')
        return False
