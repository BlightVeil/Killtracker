import requests
from time import sleep

class CM_API_Client():
    """Commander Mode API module for the Kill Tracker."""    
    def post_heartbeat_death_event(self, target_name:str, killed_zone:str) -> None:
        """Currently only support death events from the player!"""
        try:
            if not self.api_key["value"]:
                self.log.error("Error: death event will not be sent because the key does not exist.")
                return
            if not self.heartbeat_status["active"]:
                self.log.debug("Error: Heartbeat is not active. Death event will not be sent.")
                return

            url = f"{self.api_fqdn}/validateKey" # API endpoint is setup to receive heartbeats
            heartbeat_death = {
                'is_heartbeat': True,
                'player': target_name,
                'zone': killed_zone,
                'client_ver': "7.0",
                'status': "dead",  # Report status as 'dead'
                'mode': "commander"
            }
            headers = {
                'content-type': 'application/json',
                'Authorization': self.api_key["value"] if self.api_key["value"] else ""
            }
            self.log.debug(f"post_heartbeat_death_event(): Request payload: {heartbeat_death}")
            response = requests.post(
                url, 
                headers=headers, 
                json=heartbeat_death, 
                timeout=self.request_timeout
            )
            self.log.debug(f"post_heartbeat_death_event(): Response text: {response.text}")
            if response.status_code != 200:
                self.log.error(f"Error in posting death event: code {response.status_code}")
                self.log.error(f"Error: death event {heartbeat_death} will not be sent!")
        except requests.exceptions.RequestException as e:
            self.log.error(f"HTTP Error sending kill event: {e}")
            self.log.error(f"Error: death event {heartbeat_death} will not be sent!")
        except Exception as e:
            self.log.error(f"post_heartbeat_death_event(): Error: {e.__class__.__name__} {e}")

    def post_heartbeat_enter_ship_event(self, player_ship:str) -> None:
        """Update the ship and set player to alive with heartbeat!"""
        try:
            if not self.api_key["value"]:
                self.log.error("Error: death event will not be sent because the key does not exist.")
                return
            if not self.heartbeat_status["active"]:
                self.log.debug("Error: Heartbeat is not active. Enter ship event will not be sent.")
                return

            url = f"{self.api_fqdn}/validateKey" # API endpoint is setup to receive heartbeats
            heartbeat_enter_ship = {
                'is_heartbeat': True,
                'player': self.rsi_handle["current"],
                'zone': player_ship,
                'client_ver': "7.0",
                'status': "alive",  # Report status as 'alive'
                'mode': "commander"
            }
            headers = {
                'content-type': 'application/json',
                'Authorization': self.api_key["value"] if self.api_key["value"] else ""
            }
            self.log.debug(f"post_heartbeat_enter_ship_event(): Request payload: {heartbeat_enter_ship}")
            response = requests.post(
                url,
                headers=headers,
                json=heartbeat_enter_ship,
                timeout=self.request_timeout
            )
            self.log.debug(f"post_heartbeat_enter_ship_event(): Response text: {response.text}")
            if response.status_code != 200:
                self.log.error(f"Error in posting enter ship event: code {response.status_code}")
                self.log.error(f"Error: enter ship event {heartbeat_enter_ship} will not be sent!")
        except requests.exceptions.RequestException as e:
            self.log.error(f"HTTP Error sending enter ship event: {e}")
            self.log.error(f"Error: enter ship event {heartbeat_enter_ship} will not be sent!")
        except Exception as e:
            self.log.error(f"post_heartbeat_enter_ship_event(): Error: {e.__class__.__name__} {e}")

    def post_heartbeat(self) -> None:
        """Sends a heartbeat to the server every interval and updates the UI with active commanders."""        
        while self.heartbeat_status["active"]:
            try:
                sleep(self.heartbeat_interval)
                if not self.api_key["value"]:
                    self.log.warning("Error: heartbeat will not be sent because the key does not exist.")
                    # Call disconnect commander and exit
                    self.toggle_commander()
                    break
                
                url = f"{self.api_fqdn}/validateKey"
                # Determine status based on the active ship
                status = "alive" if self.active_ship["current"] != "N/A" else "dead"
                heartbeart_base = {
                    'is_heartbeat': True,
                    'player': self.rsi_handle["current"],
                    'zone': self.active_ship["current"],
                    'client_ver': "7.0",
                    'status': status,
                    'mode': "commander"
                }
                headers = {
                    'content-type': 'application/json',
                    'Authorization': self.api_key["value"] if self.api_key["value"] else ""
                }
                #self.log.debug(f"post_heartbeat(): Request payload: {heartbeart_base}")
                response = requests.post(
                    url, 
                    headers=headers, 
                    json=heartbeart_base, 
                    timeout=self.request_timeout
                )
                self.log.debug(f"post_heartbeat(): Response text: {response.text}")
                response.raise_for_status()  # Raises an exception for HTTP errors
                response_data = response.json()
                # Update the UI with active commanders if the response contains the key
                if 'commanders' in response_data:
                    active_commanders = response_data['commanders']
                    # Put the updated commanders list in the queue for the GUI thread to process
                    self.update_queue.put(active_commanders)
                else:
                    self.log.debug("No commanders found in response.")
            except requests.RequestException as e:
                self.log.error(f"HTTP Error when sending heartbeat: {e}")
            except Exception as e:
                self.log.error(f"post_heartbeat(): Error: {e.__class__.__name__} {e}")
