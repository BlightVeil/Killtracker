from typing import Union

import requests
from time import sleep

class CM_API_Client():
    """Commander Mode API module for the Kill Tracker."""

    def post_heartbeat_event(self, target_name: Union[str, None], killed_zone: Union[str, None], player_ship: Union[str, None]) -> None:
        """Currently only support death events from the player!"""
        try:
            if not self.api_key["value"]:
                self.log.error("Death event will not be sent because the key does not exist.")
                return
            if not self.heartbeat_status["active"]:
                self.log.debug("Error: Heartbeat is not active. Death event will not be sent.")
                return

            url = f"{self.api_fqdn}/validateKey" # API endpoint is setup to receive heartbeats
            status = "alive" if self.active_ship["current"] != "N/A" else "dead"
            heartbeat_event = {
                'is_heartbeat': True,
                'player': self.rsi_handle["current"],
                'zone': self.active_ship["current"],
                'client_ver': "7.0",
                'status': status,  # Report status as 'dead'
                'is_commander': self.is_commander,
                'mark_complete': self.mark_complete,
                'start_battle': self.start_battle,
                'abort_command': self.abort_command,
            }
            if killed_zone is not None:
                heartbeat_event['player'] = target_name
                heartbeat_event['zone'] = killed_zone
                heartbeat_event['status'] = "dead"
            elif player_ship is not None:
                heartbeat_event['zone'] = player_ship
                heartbeat_event['status'] = "alive"
            # If it's not either of the above if/else statements, its probably a flag update!
            headers = {
                'content-type': 'application/json',
                'Authorization': self.api_key["value"] if self.api_key["value"] else ""
            }
            self.log.debug(f"post_heartbeat_event(): Request payload: {heartbeat_event}")
            response = requests.post(
                url,
                headers=headers,
                json=heartbeat_event,
                timeout=self.request_timeout
            )
            self.log.debug(f"post_heartbeat_event(): Response text: {response.text}")
            if response.status_code != 200:
                self.log.error(f"When posting event: code {response.status_code}")
                self.log.error(f"Event will not be sent! Event dump: {heartbeat_event}")
        except requests.exceptions.RequestException as e:
            self.log.error(f"HTTP Error sending kill event: {e}")
            self.log.error(f"Event will not be sent! Event dump: {heartbeat_event}")
        except Exception as e:
            self.log.error(f"post_heartbeat_event(): {e.__class__.__name__} {e}")

    def post_heartbeat(self) -> None:
        """Sends a heartbeat to the server every interval and updates the UI with active commanders."""        
        while self.heartbeat_status["active"]:
            try:
                sleep(self.heartbeat_interval)
                if not self.api_key["value"]:
                    self.log.warning("Heartbeat will not be sent because the key does not exist.")
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
                    'mode': "commander",
                    'is_commander': self.is_commander,
                }
                if self.is_commander is True:
                    heartbeart_base['alloc_users'] = self.alloc_users if self.alloc_users else None
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
                self.log.error(f"post_heartbeat(): {e.__class__.__name__} {e}")
