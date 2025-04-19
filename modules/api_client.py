import requests
import webbrowser
from packaging import version

class API_Client():
    def check_for_kt_updates(self) -> str:
        """Check for updates using the GitHub API."""
        github_api_url = "https://api.github.com/repos/BlightVeil/Killtracker/releases/latest"

        try:
            headers = {'User-Agent': 'Killtracker/1.3'}
            response = requests.get(github_api_url, headers=headers, timeout=5)

            if response.status_code == 200:
                release_data = response.json()
                remote_version = release_data.get("tag_name", "v1.3").strip("v")
                download_url = release_data.get("html_url", "")

                if version.parse(self.local_version) < version.parse(remote_version):
                    return f"Update available: {remote_version}. Download it here: {download_url}"
            else:
                print(f"GitHub API error: {response.status_code}")
        except Exception as e:
            print(f"Error checking for updates: {e.__class__.__name__} {e}")
            return ""
        
    def open_github(self, update_message):
        try:
            url = update_message.split("Download it here: ")[-1]
            webbrowser.open(url)
        except Exception as e:
            print(f"Error opening GitHub link: {e}")

    # Trigger kill event
    def parse_kill_line(line, target_name, logger):
        global global_active_ship
        global player_status  # Add a global status variable to track player's state
        player_status = "alive"  # Default status is alive

        if not check_exclusion_scenarios(line, logger):
            return

        split_line = line.split(' ')

        kill_time = split_line[0].strip('\'')
        killed = split_line[5].strip('\'')
        killed_zone = split_line[9].strip('\'')
        killer = split_line[12].strip('\'')
        weapon = split_line[15].strip('\'')
        rsi_profile = f"https://robertsspaceindustries.com/citizens/{killed}"

        if killed == killer or killer.lower() == "unknown" or killed == target_name:
            # Log a message for the player's own death
            logger.log("You have fallen in the service of BlightVeil.")

            # Send death-event to the server via heartbeat
            post_heartbeat_death_event(target_name, killed_zone, logger)
            destroy_player_zone(line, logger)
            return

        logger.log(f"✅ You have killed {killed},")
        logger.log(f"and brought glory to the Veil.")

        json_data = {
            'player': target_name,
            'victim': killed,
            'time': kill_time,
            'zone': killed_zone,
            'weapon': weapon,
            'rsi_profile': rsi_profile,
            'game_mode': game_mode,
            'client_ver': "7.0",
            'killers_ship': global_active_ship,
            'anonymize_state': anonymize_state
        }

        headers = {
            'content-type': 'application/json',
            'Authorization': api_key["value"] if api_key["value"] else ""
        }

        if not api_key["value"]:
            logger.log("Kill event will not be sent. Enter valid key to establish connection with Servitor...")
            return

        try:
            response = requests.post(
                "http://drawmyoshi.com:25966/reportKill",
                headers=headers,
                data=json.dumps(json_data),
                timeout=30
            )
            if response.status_code == 200:
                play_random_sound(logger)
                logger.log("and brought glory to the Veil.")
            else:
                logger.log(f"⚠️ Servitor connectivity error: {response.status_code}.")
                logger.log("⚠️ Relaunch BV Kill Tracker and reconnect with a new Key.")
        except requests.exceptions.RequestException as e:
            async_loading_animation(logger, app)
            logger.log(f"⚠️ Error sending kill event: {e}")
            logger.log("⚠️ Kill event will not be sent. Please ensure a valid key and try again.")
        except Exception as e:
            logger.log(f"⚠️ Error when parsing kill: {e.__class__.__name__} {e}")

    def post_heartbeat_death_event(target_name, killed_zone, logger):
        """Currently only support death events from the player!"""
        json_data = {
            'is_heartbeat': True,
            'player': target_name,
            'zone': killed_zone,
            'client_ver': "7.0",
            'status': "dead",  # Report status as 'dead'
            'mode': "commander"
        }

        headers = {
            'content-type': 'application/json',
            'Authorization': api_key["value"] if api_key["value"] else ""
        }

        try:
            response = requests.post(
                "http://drawmyoshi.com:25966/validateKey",
                headers=headers,
                data=json.dumps(json_data),
                timeout=5
            )
            if response.status_code != 200:
                logger.log(f"Failed to report death event: {response.status_code}.")
        except Exception as e:
            logger.log(f"Error reporting death event: {e}")

    def post_heartbeat_enter_ship_event(self, player_ship):
        """Update the ship and set player to alive with heartbeat!"""
        json_data = {
            'is_heartbeat': True,
            'player': self.rsi_handle,
            'zone': player_ship,
            'client_ver': "7.0",
            'status': "alive",  # Report status as 'alive'
            'mode': "commander"
        }

        headers = {
            'content-type': 'application/json',
            'Authorization': api_key["value"] if api_key["value"] else ""
        }

        try:
            response = requests.post(
                "http://drawmyoshi.com:25966/validateKey",
                headers=headers,
                data=json.dumps(json_data),
                timeout=5
            )
            if response.status_code != 200:
                logger.log(f"Failed to report ship status event: {response.status_code}.")
        except Exception as e:
            logger.log(f"Error reporting ship status event: {e}")

    def post_heartbeat(self):
        """Sends a heartbeat to the server every 5 seconds and updates the UI with active commanders."""
        heartbeat_url = "http://drawmyoshi.com:25966/validateKey"
        headers = {
            'content-type': 'application/json',
            'Authorization': api_key["value"] if api_key["value"] else ""
        }
        global_heartbeat_active = True

        while global_heartbeat_active:
            time.sleep(5)
            # Determine status based on the active ship
            status = "alive" if global_active_ship != "N/A" else "dead"

            json_data = {
                'is_heartbeat': True,
                'player': self.rsi_handle,
                'zone': global_active_ship,
                'client_ver': "7.0",
                'status': status,
                'mode': "commander"
            }

            if not api_key["value"]:
                logger.log("Heartbeat will not be sent. Enter valid key to establish connection with Servitor...")
                global_heartbeat_active = False
                return

            try:
                # logger.log(f"Sending heartbeat: {json_data}")
                response = requests.post(heartbeat_url, headers=headers, json=json_data, timeout=5)
                response.raise_for_status()  # Raises an exception for HTTP errors

                response_data = response.json()
                # logger.log(f"Received response: {response_data}")

                # Update the UI with active commanders if the response contains the key
                if 'commanders' in response_data:
                    active_commanders = response_data['commanders']
                    # Put the updated commanders list in the queue for the GUI thread to process
                    update_queue.put(active_commanders)
                else:
                    logger.log("No commanders found in response.")

            except requests.RequestException as e:
                logger.log(f"Error sending heartbeat: {e}")
                global_heartbeat_active = False
                return        

    def start_heartbeat_thread(logger):
        """Start the heartbeat in a separate thread."""
        global global_heartbeat_active
        global global_heartbeat_daemon
        if global_heartbeat_active:
            logger.log("Already connected to commander!")
            return
        logger.log("Connecting to commander...")
        global_heartbeat_daemon = threading.Thread(target=post_heartbeat, args=())
        global_heartbeat_daemon.daemon = True
        global_heartbeat_daemon.start()

    def stop_heartbeat_thread(logger):
        global global_heartbeat_active
        global global_heartbeat_daemon
        if global_heartbeat_active:
            logger.log("Flagging heartbeat to shut down")
            global_heartbeat_active = False
            global_heartbeat_daemon.join()
            return

    def run_api_key_expiration_check(api_key):
        """Run get_api_key_expiration_time in a separate thread."""
        thread = threading.Thread(target=get_api_key_expiration_time, args=(api_key,))
        thread.daemon = True  # Ensures the thread exits when the program closes
        thread.start()

    def start_api_key_countdown(api_key, api_status_label):
        """Start the countdown for the API key's expiration, refreshing expiry data periodically."""
        def fetch_expiration_time():
            """Fetch expiration time in a separate thread and update countdown."""
            def threaded_request():
                expiration_time = get_api_key_expiration_time(api_key)  # Fetch latest expiration time
                if not expiration_time:
                    api_status_label.config(text="API Status: Expired", fg="red")
                    return

                def countdown():
                    remaining_time = expiration_time - datetime.datetime.utcnow()
                    if remaining_time.total_seconds() > 0:
                        hours, remainder = divmod(remaining_time.seconds, 3600)
                        minutes, seconds = divmod(remainder, 60)
                        countdown_text = f"API Status: Valid (Expires in {remaining_time.days}d {hours}h {minutes}m {seconds}s)"
                        api_status_label.config(text=countdown_text, fg="green")
                        api_status_label.after(1000, countdown)  # Update every second
                    else:
                        api_status_label.config(text="API Status: Expired", fg="red")

                countdown()

                # Refresh expiration time every 60 seconds in a new thread
                api_status_label.after(60000, fetch_expiration_time)

            thread = threading.Thread(target=threaded_request)
            thread.daemon = True
            thread.start()

        fetch_expiration_time()  # Initial call

    def get_api_key_expiration_time(api_key):
        """Retrieve the expiration time for the API key from the validation server."""
        url = "http://drawmyoshi.com:25966/validateKey"
        headers = {
            "Authorization": api_key,
            "Content-Type": "application/json"
        }
        data = {
            "player_name": self.rsi_handle
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                response_data = response.json()
                expiration_time_str = response_data.get("expires_at")
                if expiration_time_str:
                    return datetime.datetime.strptime(expiration_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                else:
                    logger.log("⚠️ Error: 'expires_at' not found in response")
            else:
                print("Error fetching expiration time:", response.json().get("error", "Unknown error"))
        except requests.RequestException as e:
            print(f"API request error: {e}")

        # Fallback: Expire immediately if there's an error
        return None