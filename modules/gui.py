import tkinter as tk
from tkinter import scrolledtext
from threading import Thread
from time import sleep
from datetime import datetime
from os import path

# Import kill tracker modules
import modules.helpers as Helpers
# Import global settings
import global_settings

#########################################################################################################
### LOGGER CLASS                                                                                      ###
#########################################################################################################

class AppLogger():
    """Writes log lines to the GUI."""
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def Decorator(log_writer):
        def widget_handler(self, message):
            self.text_widget.config(state=tk.NORMAL)
            log_time = datetime.now().strftime("%X")
            log_writer(self, log_time, message)
            self.text_widget.config(state=tk.DISABLED)
            self.text_widget.see(tk.END)
        return widget_handler
    
    @Decorator
    def debug(self, log_time, message):
        if global_settings.DEBUG_MODE["enabled"]:
            self.text_widget.insert(tk.END, log_time + " DEBUG: " + message + "\n")

    @Decorator
    def info(self, log_time, message):
        self.text_widget.insert(tk.END, log_time + " " + message + "\n")

    @Decorator
    def warning(self, log_time, message):
        self.text_widget.insert(tk.END, log_time + " ⚠️ WARNING: " + message + "\n")

    @Decorator
    def error(self, log_time, message):
        self.text_widget.insert(tk.END, log_time + " ❌ ERROR: " + message + "\n")

    @Decorator
    def success(self, log_time, message):
        self.text_widget.insert(tk.END, log_time + " ✅ SUCCESS: " + message + "\n")

#########################################################################################################
### GUI CLASS                                                                                         ###
#########################################################################################################

class GUI():
    """GUI for the Kill Tracker."""
    def __init__(self, cfg_handler, local_version, anonymize_state, mute_state):
        self.cfg_handler = cfg_handler
        self.local_version = local_version
        self.anonymize_state = anonymize_state
        self.mute_state = mute_state
        self.app = None
        self.log = None
        self.sounds = None
        self.api = None
        self.cm = None
        self.key_entry = None
        self.api_status_label = None
        self.volume_slider = None
        self.curr_killstreak_label = None
        self.max_killstreak_label = None
        self.session_kills_label = None
        self.commander_mode_button = None
        self.init_run = True

    def setup_app_log_display(self):
        """Setup app logging in a text display area."""
        text_area = scrolledtext.ScrolledText(
            self.app, wrap=tk.WORD, width=100, height=20, state=tk.DISABLED, bg="#282a36", fg="#f8f8f2", font=("Consolas", 12)
        )
        return text_area
    
    def toggle_anonymize(self):
        """Handle anonymize button."""
        if self.anonymize_state["enabled"]:
            self.anonymize_state["enabled"] = False
            self.anonymize_button.config(text=" Enable Anonymity ", fg="#ffffff", bg="#000000")
            self.log.info(f"You are not anonymous.")
        else:
            self.anonymize_state["enabled"] = True
            self.anonymize_button.config(text="Anonymity Enabled", fg="#000000", bg="#04B431")
            self.log.info(f"You are anonymous.")

    def toggle_debug(self):
        """Handle debug button."""
        if global_settings.DEBUG_MODE["enabled"]:
            global_settings.DEBUG_MODE["enabled"] = False
            self.debug_button.config(text=" Enable Debug Mode ", fg="#ffffff", bg="#000000")
            self.log.info(f"Turned off Debug Mode.")
        else:
            global_settings.DEBUG_MODE["enabled"] = True
            self.debug_button.config(text="Debug Mode Enabled", fg="#000000", bg="#04B431")
            self.log.info(f"Turned on Debug Mode.")

    def toggle_mute(self):
        """Handle mute button."""
        if self.mute_state["enabled"]:
            self.mute_state["enabled"] = False
            # Call volume change
            self.sounds.set_volume(-1.0)
            self.mute_button.config(text="🔊", fg="#ffffff", bg="#484759")
        else:
            self.mute_state["enabled"] = True
            # Call volume change
            self.sounds.set_volume(-1.0)
            self.mute_button.config(text="🔇", fg="#ffffff", bg="#8A0000")

    def handle_volume(self, volume):
        """Handle volume."""
        if self.init_run:
            # Hack to avoid overriding initial volume setting loading from cfg
            self.init_run = False
        else:
            # Unmute volume if slider is changed
            self.mute_state["enabled"] = False
            self.mute_button.config(text="🔊", fg="#ffffff", bg="#484759")
            self.sounds.set_volume(volume)

    def update_vehicle_status(self, status_text):
        """Handle vehicle status."""
        if hasattr(self, 'vehicle_status_label') and self.vehicle_status_label:
            self.vehicle_status_label.config(text=f"Vehicle Status: {status_text}")
            #self.app.update_idletasks() 
        else:
            self.log.error("update_vehicle_status(): label is not set or does not exist.")

    def async_loading_animation(self) -> None:
        def animate():
            try:
                for dots in [".", "..", "..."]:
                    self.log.info(dots)
                    self.app.update_idletasks()
                    sleep(0.2)
            except Exception as e:
                self.log.error(f"animate(): {e.__class__.__name__} {e}")
                return
        Thread(target=animate, daemon=True).start()
    
    def create_label(
            self, window=None, text:str=None, font:str=None, command=None, bg:str=None, fg:str=None, wraplength:int=None, justify:str=None, cursor:str=None) -> tk.Label:
        """Setup label."""
        label = tk.Label(
            master=window,
            text=text,
            font=font,
            command=command,
            bg=bg,
            fg=fg,
            wraplength=wraplength,
            justify=justify,
            cursor=cursor
        )
        return label

    def create_button(self, window=None, text: str = None, font: tuple = None, command=None, bg: str = None, fg: str = None, height: int = None, width: int = None) -> tk.Button:
        """Setup button."""
        button = tk.Button(
            master=window,
            text=text,
            font=font,
            command=command,
            bg=bg,
            fg=fg,
            height=height,
            width=width
        )
        return button

    def add_module_buttons(self):
        """Add buttons for modules."""
        # API Key Input Frame
        key_frame = tk.Frame(self.app, bg="#484759")
        key_frame.pack(padx=(0, 0), pady=(20, 10))

        key_label = self.create_label(
            key_frame, text="Enter Key:", font=("Times New Roman", 12), fg="#ffffff", bg="#484759"
        )
        key_label.pack(side=tk.LEFT, pady=(0, 0))

        self.key_entry = tk.Entry(key_frame, width=30, font=("Times New Roman", 12))
        self.key_entry.pack(side=tk.LEFT, pady=(0, 0))

        # Status Frame
        status_frame = tk.Frame(self.app, bg="#484759")
        status_frame.pack(fill='both', expand=True, padx=(75, 75), pady=(20, 10))
        
        # Vehicle Status Label
        self.vehicle_status_label = self.create_label(
            status_frame, text="Vehicle Status: N/A", font=("Times New Roman", 12, 'bold'), fg="#FFD700", bg="#484759"
        )
        self.vehicle_status_label.pack(side=tk.LEFT, padx=(50, 0), pady=(0, 0))
        
        # API Status Label
        self.api_status_label = self.create_label(
            status_frame, text="Key Status: Not Validated", font=("Times New Roman", 12, 'bold'), fg="#ff0000", bg="#484759"
        )
        self.api_status_label.pack(side=tk.RIGHT, padx=(0, 50), pady=(0, 0))

        # Kill Frame
        kill_frame = tk.Frame(self.app, bg="#484759")
        kill_frame.pack(pady=(10, 10))

        # Current Killstreak Label
        self.curr_killstreak_label = self.create_label(
            kill_frame, text="Current Killstreak: 0", font=("Times New Roman", 12, 'bold'), fg="#ffffff", bg="#484759"
        )
        self.curr_killstreak_label.pack(side=tk.LEFT, padx=(0, 20), pady=(0, 0))

        # Max KillStreak Label
        self.max_killstreak_label = self.create_label(
            kill_frame, text="Max Killstreak: 0", font=("Times New Roman", 12, 'bold'), fg="#ffffff", bg="#484759"
        )
        self.max_killstreak_label.pack(side=tk.LEFT, padx=(0, 20), pady=(0, 0))

        # Kills Total Label
        self.session_kills_label = self.create_label(
            kill_frame, text="Total Session Kills: 0", font=("Times New Roman", 12, 'bold'), fg="#ffffff", bg="#484759"
        )
        self.session_kills_label.pack(side=tk.LEFT, padx=(0, 20), pady=(0, 0))

        # Deaths Total Label
        self.session_deaths_label = self.create_label(
            kill_frame, text="Total Session Deaths: 0", font=("Times New Roman", 12, 'bold'), fg="#ffffff", bg="#484759"
        )
        self.session_deaths_label.pack(side=tk.LEFT, padx=(0, 20), pady=(0, 0))
        
        # KD Ratio Label
        self.kd_ratio_label = self.create_label(
            kill_frame, text="KD Ratio: --", font=("Times New Roman", 12, 'bold'), fg="#00FFFF", bg="#484759"
        )
        self.kd_ratio_label.pack(side=tk.RIGHT, padx=(0, 20), pady=(0, 0))

        # Update the button to use the new combined function
        activate_load_key_button = self.create_button(
            key_frame, text="Activate & Load Key", font=("Times New Roman", 12), command=self.api.load_activate_key, fg="#ffffff", bg="#000000"
        )
        activate_load_key_button.pack(side=tk.LEFT, padx=(5, 0))

        # Options Frame
        options_frame = tk.Frame(self.app, bg="#484759")
        options_frame.pack(pady=(0, 0))

        # Commander Mode Button
        self.commander_mode_button = self.create_button(
            options_frame, text="Commander Mode", font=("Times New Roman", 12), command=self.cm.setup_commander_mode, fg="#ffffff", bg="#000000"
        )
        self.commander_mode_button.pack(side=tk.LEFT, pady=(0, 0))

        self.anonymize_button = self.create_button(
            options_frame, text=" Enable Anonymity ", font=("Times New Roman", 12), command=self.toggle_anonymize, fg="#ffffff", bg="#000000"
        )
        self.anonymize_button.pack(side=tk.LEFT, padx=(5, 0))

        self.debug_button = self.create_button(
            options_frame, text=" Enable Debug Mode ", font=("Times New Roman", 12), command=self.toggle_debug, fg="#ffffff", bg="#000000"
        )
        self.debug_button.pack(side=tk.LEFT, padx=(5, 0), pady=(5, 5))

        self.mute_button = self.create_button(
            options_frame, text="🔊", font=("Times New Roman", 14), command=self.toggle_mute, fg="#ffffff", bg="#484759", height=0, width=3
        )
        self.mute_button.pack(side=tk.LEFT, padx=(50, 0))

        self.volume_slider = tk.Scale(
            options_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            length=200,
            bg="#484759",
            fg="#ffffff",
            troughcolor="#282a36",
            highlightbackground="#484759",
            command=lambda val: self.handle_volume(int(val) / 100)
        )
        self.volume_slider.set(self.cfg_handler.cfg_dict["volume"]["level"] * 100)  # Default volume to 50%
        self.volume_slider.pack(side=tk.LEFT, padx=(5, 0), pady=(0, 15))
        
        # App logger area
        self.log = AppLogger(self.setup_app_log_display())
        self.log.text_widget.pack(padx=10, pady=10)

    def setup_gui(self, game_running):
        """Setup the GUI."""
        # Init setup
        try:
            self.app = tk.Tk(useTk=True)
            self.app.title(f"BlightVeil Kill Tracker v{self.local_version}")
            self.app.minsize(width=890, height=890)
            self.app.configure(bg="#484759")
        except Exception as e:
            print(f"setup_gui(): ERROR: Init setup failed: {e.__class__.__name__} {e}")
        
        # Set the icon
        try:
            icon_path = Helpers.resource_path("static/BlightVeil.ico")
            if path.exists(icon_path):
                self.app.iconbitmap(icon_path)
                #print(f"Icon loaded successfully from: {icon_path}")
            else:
                print(f"setup_gui(): ERROR: icon not found at: {icon_path}")
        except Exception as e:
            print(f"setup_gui(): ERROR: setting icon failed: {e.__class__.__name__} {e}")

        # Render the banner
        try:
            banner_path = Helpers.resource_path("static/BlightVeilBanner.png")
            if path.exists(banner_path):
                #self.log.success(f"Banner image loaded successfully from: {banner_path}")
                banner_image = tk.PhotoImage(file=banner_path)
                banner_label = tk.Label(self.app, image=banner_image, bg="#484759")
                banner_label.image = banner_image
                banner_label.pack(pady=(10, 0))
            else:
                print(f"setup_gui(): ERROR: banner not found at: {icon_path}")
        except Exception as e:
            print(f"setup_gui(): Error loading banner image: {e.__class__.__name__} {e}")

        # Check for Updates
        try:
            update_message = self.api.check_for_kt_updates()
            if update_message:
                update_label = self.create_label(
                    self.app, text=update_message, font=("Times New Roman", 12), wraplength=700, justify="center", cursor="hand2", fg="#ff5555", bg="#484759"
                )
                update_label.pack(pady=(10, 10))
                update_label.bind("<Button-1>", self.api.open_github(update_message))
        except Exception as e:
            print(f"setup_gui(): Error checking for Kill Tracker updates: {e.__class__.__name__} {e}")

        if not game_running:
            try:
                # Relaunch Message
                message_label = self.create_label(
                    self.app,
                    text="You must launch Star Citizen before starting the Kill Tracker.\n\nPlease close this window, launch Star Citizen, and relaunch the Kill Tracker. ",
                    font=("Times New Roman", 14),
                    fg="#000000",
                    bg="#484759",
                    wraplength=700,
                    justify="center"
                )
                message_label.pack(pady=(50, 10))
                #self.log = None #FIXME Why is this here?
            except Exception as e:
                print(f"setup_gui(): Error rendering the relaunch message: {e.__class__.__name__} {e}")
        else:
            try:
                # Add GUI buttons if game running
                self.add_module_buttons()
            except Exception as e:
                print(f"setup_gui(): Error rendering the module buttons: {e.__class__.__name__} {e}")
        
        # Footer
        try:
            footer = tk.Frame(self.app, bg="#3e3b4d", height=30)
            footer.pack(side=tk.BOTTOM, fill=tk.X)

            footer_text = self.create_label(
                footer,
                text="BlightVeil Kill Tracker - Credits: CyberBully-Actual, BossGamer09, Holiday, SamuraiZero",
                font=("Times New Roman", 10),
                fg="#bcbcd8",
                bg="#3e3b4d",
            )
            footer_text.pack(pady=(5, 5))
        except Exception as e:
            print(f"setup_gui(): Error rendering the footer: {e.__class__.__name__} {e}")
