import tkinter as tk
from tkinter import scrolledtext
from os import path

# Import kill tracker modules
from api_client import check_for_kt_updates, open_github
import modules.helpers as Helpers

#########################################################################################################
### LOGGER CLASS                                                                                      ###
#########################################################################################################

class AppLogger():
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def Decorator(log_writer):
        def widget_handler(self, message):
            self.text_widget.config(state=tk.NORMAL)
            log_writer(self, message)
            self.text_widget.config(state=tk.DISABLED)
            self.text_widget.see(tk.END)
        return widget_handler
    
    @Decorator
    def debug(self, message):
        self.text_widget.insert(tk.END, "DEBUG " + message + "\n")

    @Decorator
    def info(self, message):
        self.text_widget.insert(tk.END, message + "\n")

    @Decorator
    def warning(self, message):
        self.text_widget.insert(tk.END, "⚠️ " + message + "\n")

    @Decorator
    def error(self, message):
        self.text_widget.insert(tk.END, "❌ " + message + "\n")

    @Decorator
    def success(self, message):
        self.text_widget.insert(tk.END, "✅ " + message + "\n")


class B():
    def __init__(self, logger) -> None:
        self.log = logger
        
b = B(app_logger)
b.log.success("hi")
self.log.error("derp")

#########################################################################################################
### GUI CLASS                                                                                         ###
#########################################################################################################

class GUI():
    """Build and launch the GUI for the KillTracker."""
    def __init__(self, local_version):
        self.local_version = local_version
        self.app = tk.Tk()
        self.log = AppLogger(self.setup_app_log_display()) 

    def setup_app_log_display(self):
        """Setup app logging in a text display area."""
        text_area = scrolledtext.ScrolledText(
            self.app, wrap=tk.WORD, width=80, height=20, state=tk.DISABLED, bg="#282a36", fg="#f8f8f2", font=("Consolas", 12)
        )
        return text_area

    def setup_gui(self, game_running):
        self.app.title(f"BlightVeil Kill Tracker v{self.local_version}")
        self.app.geometry("800x800")
        self.app.configure(bg="#484759")

        # Set the icon
        try:
            icon_path = Helpers.resource_path("static/BlightVeil.ico")
            if path.exists(icon_path):
                self.app.iconbitmap(icon_path)
                self.log.success(f"Icon loaded successfully from: {icon_path}")
            else:
                self.log.error(f"setup_gui(): ERROR: icon not found at: {icon_path}")
        except Exception as e:
            self.log.error(f"setup_gui(): ERROR: setting icon failed: {e.__class__.__name__} {e}")

        # Render the banner
        try:
            banner_path = Helpers.resource_path("static/BlightVeilBanner.png")
            if path.exists(banner_path):
                self.log.success(f"Banner image loaded successfully from: {banner_path}")
                banner_image = tk.PhotoImage(file=banner_path)
                banner_label = tk.Label(self.app, image=banner_image, bg="#484759")
                banner_label.image = banner_image
                banner_label.pack(pady=(0, 10))
            else:
                self.log.error(f"setup_gui(): ERROR: banner not found at: {icon_path}")
        except Exception as e:
            self.log.error(f"Error loading banner image: {e.__class__.__name__} {e}")

        # Check for Updates
        update_message = check_for_kt_updates()
        if update_message:
            update_label = tk.Label(
                self.app,
                text=update_message,
                font=("Times New Roman", 12),
                fg="#ff5555",
                bg="#484759",
                wraplength=700,
                justify="center",
                cursor="hand2",
            )
            update_label.pack(pady=(10, 10))
            update_label.bind("<Button-1>", open_github(update_message))

        if not game_running:
            # Relaunch Message
            message_label = tk.Label(
                self.app,
                text="You must launch Star Citizen before starting the tracker.\n\nPlease close this window, launch Star Citizen, and relaunch the BV Kill Tracker. ",
                font=("Times New Roman", 14),
                fg="#000000",
                bg="#484759",
                wraplength=700,
                justify="center",
            )
            message_label.pack(pady=(50, 10))
            self.log = None
        else:
            # API Key Input
            key_frame = tk.Frame(self.app, bg="#484759")
            key_frame.pack(pady=(10, 10))

            key_label = tk.Label(
                key_frame, text="Enter Key:", font=("Times New Roman", 12), fg="#ffffff", bg="#484759"
            )
            key_label.pack(side=tk.LEFT, padx=(0, 5))

            key_entry = tk.Entry(key_frame, width=30, font=("Times New Roman", 12))
            key_entry.pack(side=tk.LEFT)

            # API Status Label
            api_status_label = tk.Label(
                self.app,
                text="API Status: Not Validated",
                font=("Times New Roman", 12),
                fg="#ffffff",
                bg="#484759",
            )
            api_status_label.pack(pady=(10, 10))

            def activate_and_load_key():

                def validate_api_key(api_key):
                    url = "http://drawmyoshi.com:25966/validateKey"
                    headers = {
                        "Authorization": api_key,
                        "Content-Type": "application/json"
                    }
                    data = {
                        "api_key": api_key,
                        "player_name": self.rsi_handle
                    }

                    try:
                        response = requests.post(url, headers=headers, json=data)
                        if not response.status_code == 200:
                            logger.log(f"❌ API for key validation returned code {response.status_code} - {response.text}")
                            return False
                        return True
                    except requests.RequestException as e:
                        logger.log(f"❌ API key validation error: {e.__class__.__name__} {e}")
                        return False
                            
                def save_api_key(key):
                    try:
                        with open("killtracker_key.cfg", "w") as f:
                            f.write(key)
                        api_key["value"] = key  # Make sure to save the key in the global api_key dictionary as well
                        logger.log(f"✅ API key saved successfully: {key}")
                    except Exception as e:
                        logger.log(f"❌ Error saving API key: {e.__class__.__name__} {e}")

                try:
                    entered_key = key_entry.get().strip()  # Access key_entry here
                except Exception as e:
                    logger.log(f"❌ Error parsing API key: {e.__class__.__name__} {e}")

                try:
                    if not entered_key:
                        logger.log("⚠️ No key was entered. Attempting to load saved key if it exists...")
                        with open("killtracker_key.cfg", "r") as f:
                            entered_key = f.readline().strip()
                            if entered_key:
                                api_key["value"] = entered_key  # Assign the loaded key
                                logger.log(f"Saved key loaded: {entered_key}. Attempting to establish Servitor connection...")
                except FileNotFoundError:
                    logger.log("⚠️ No saved key found. Please enter a valid key.")
                    api_status_label.config(text="API Status: Invalid", fg="red")

                try:
                    # Proceed with activation
                    log_file_location = get_sc_log_location(logger)
                    if log_file_location:
                        get_player_name(log_file_location) # Get the global RSI handle
                        if self.rsi_handle:
                            if validate_api_key(entered_key):  # Pass both the key and player name
                                save_api_key(entered_key)  # Save the key for future use
                                logger.log("✅ Key activated and saved. Servitor connection established.")
                                logger.log("✅ Go Forth And Slaughter...")
                                api_status_label.config(text="API Status: Valid (Expires in 72 hours)", fg="green")
                                start_api_key_countdown(entered_key, api_status_label)
                            else:
                                logger.log("⚠️ Invalid key or player name. Please enter a valid API key.")
                                api_status_label.config(text="API Status: Invalid", fg="red")
                        else:
                            logger.log("⚠️ RSI Handle not found. Please ensure the game is running and the log file is accessible.")
                            api_status_label.config(text="API Status: Error", fg="yellow")
                    else:
                        logger.log("⚠️ Log file location not found.")
                        api_status_label.config(text="API Status: Error", fg="yellow")
                except Exception as e:
                    logger.log(f"❌ Error parsing API key: {e.__class__.__name__} {e}")
            print('b')
            # Update the button to use the new combined function
            activate_load_key_button = tk.Button(
                key_frame,
                text="Activate & Load Key",
                font=("Times New Roman", 12),
                command=activate_and_load_key(),
                bg="#000000",
                fg="#ffffff",
            )
            activate_load_key_button.pack(side=tk.LEFT, padx=(5, 0))

            # Commander Mode Button
            commander_mode_button = tk.Button(
                self.app,
                text="Commander Mode",
                font=("Times New Roman", 12),
                command=lambda: open_commander_mode(logger),
                bg="#000000",
                fg="#ffffff",
            )
            commander_mode_button.pack(pady=(10, 10)) 

            text_area.pack(padx=10, pady=10)

            logger = AppLogger(text_area)
            
            # Define the function to toggle the state
            def toggle_anonymize():
                if anonymize_state["enabled"]:
                    anonymize_state["enabled"] = False
                    anonymize_button.config(text="Enable Anonymity - Not Anonymous")
                else:
                    anonymize_state["enabled"] = True
                    anonymize_button.config(text="Disable Anonymity - Anonymous")
                logger.log(f"Anonymize state changed: {anonymize_state['enabled']}")

            # Add the button to the GUI
            anonymize_button = tk.Button(
                key_frame,
                text="Enable Anonymity - Not Anonymous",
                font=("Times New Roman", 12),
                command=toggle_anonymize,
                bg="#000000",
                fg="#ffffff",
            )
            anonymize_button.pack(side=tk.LEFT, padx=(5, 0))
        

        # Footer
        footer = tk.Frame(self.app, bg="#3e3b4d", height=30)
        footer.pack(side=tk.BOTTOM, fill=tk.X)

        footer_text = tk.Label(
            footer,
            text="BlightVeil Kill Tracker - Credits: CyberBully-Actual, BossGamer09, Holiday, Samurai",
            font=("Times New Roman", 10),
            fg="#bcbcd8",
            bg="#3e3b4d",
        )
        footer_text.pack(pady=5)

        return self.app