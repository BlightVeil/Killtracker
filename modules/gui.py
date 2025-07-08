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
            self.text_widget.insert(tk.END, log_time + " DEBUG " + message + "\n")

    @Decorator
    def info(self, log_time, message):
        self.text_widget.insert(tk.END, log_time + " " + message + "\n")

    @Decorator
    def warning(self, log_time, message):
        self.text_widget.insert(tk.END, log_time + " ⚠️ " + message + "\n")

    @Decorator
    def error(self, log_time, message):
        self.text_widget.insert(tk.END, log_time + " ❌ " + message + "\n")

    @Decorator
    def success(self, log_time, message):
        self.text_widget.insert(tk.END, log_time + " ✅ " + message + "\n")

#########################################################################################################
### GUI CLASS                                                                                         ###
#########################################################################################################

class GUI():
    """GUI for the Kill Tracker."""
    def __init__(self, local_version, anonymize_state):
        self.local_version = local_version
        self.anonymize_state = anonymize_state
        self.app = None
        self.log = None
        self.api = None
        self.cm = None
        self.key_entry = None
        self.api_status_label = None
        self.curr_killstreak_label = None
        self.max_killstreak_label = None
        self.session_kills_label = None
        self.commander_mode_button = None

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
            self.log.error(f"You are not anonymous.")
        else:
            self.anonymize_state["enabled"] = True
            self.anonymize_button.config(text="Anonymity Enabled", fg="#000000", bg="#04B431")
            self.log.success(f"You are anonymous.")

    def toggle_debug(self):
        """Handle debug button."""
        if global_settings.DEBUG_MODE["enabled"]:
            global_settings.DEBUG_MODE["enabled"] = False
            self.debug_button.config(text=" Enable Debug Mode ", fg="#ffffff", bg="#000000")
            self.log.error(f"Turned off Debug Mode.")
        else:
            global_settings.DEBUG_MODE["enabled"] = True
            self.debug_button.config(text="Debug Mode Enabled", fg="#000000", bg="#04B431")
            self.log.success(f"Turned on Debug Mode.")

    def async_loading_animation(self) -> None:
        def animate():
            try:
                for dots in [".", "..", "..."]:
                    self.log.info(dots)
                    self.app.update_idletasks()
                    sleep(0.2)
            except Exception as e:
                self.log.error(f"animate(): Error: {e.__class__.__name__} {e}")
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

    def create_button(self, window=None, text: str = None, font: tuple = None, command=None, bg: str = None, fg: str = None) -> tk.Button:
        """Setup button."""
        button = tk.Button(
            master=window,
            text=text,
            font=font,
            command=command,
            bg=bg,
            fg=fg,
        )
        return button

    def add_module_buttons(self):
        """Add buttons for modules."""
        # API Key Input Frame
        key_frame = tk.Frame(self.app, bg="#484759")
        key_frame.pack(pady=(10, 10))

        key_label = self.create_label(
            key_frame, text="Enter Key:", font=("Times New Roman", 12), fg="#ffffff", bg="#484759"
        )
        key_label.pack(side=tk.LEFT, padx=(50, 5))

        self.key_entry = tk.Entry(key_frame, width=30, font=("Times New Roman", 12))
        self.key_entry.pack(side=tk.LEFT)

        # API Status Label
        self.api_status_label = self.create_label(
            self.app, text="Key Status: Not Validated", font=("Times New Roman", 12, 'bold'), fg="#ff0000", bg="#484759"
        )
        self.api_status_label.pack(pady=(10, 10))

        # Kill Frame
        kill_frame = tk.Frame(self.app, bg="#484759")
        kill_frame.pack(pady=(10, 10))

        # Current Killstreak Label
        self.curr_killstreak_label = self.create_label(
            kill_frame, text="Current Killstreak: 0", font=("Times New Roman", 12, 'bold'), fg="#ffffff", bg="#484759"
        )
        self.curr_killstreak_label.pack(side=tk.LEFT, padx=(0, 20), pady=(10, 10))

        # Max KillStreak Label
        self.max_killstreak_label = self.create_label(
            kill_frame, text="Max Killstreak: 0", font=("Times New Roman", 12, 'bold'), fg="#ffffff", bg="#484759"
        )
        self.max_killstreak_label.pack(side=tk.LEFT, padx=(0, 20), pady=(10, 10))

        # Kills Total Label
        self.session_kills_label = self.create_label(
            kill_frame, text="Total Session Kills: 0", font=("Times New Roman", 12, 'bold'), fg="#ffffff", bg="#484759"
        )
        self.session_kills_label.pack(side=tk.LEFT, padx=(0, 20), pady=(10, 10))

        # Deaths Total Label
        self.session_deaths_label = self.create_label(
            kill_frame, text="Total Session Deaths: 0", font=("Times New Roman", 12, 'bold'), fg="#ffffff", bg="#484759"
        )
        self.session_deaths_label.pack(side=tk.LEFT, padx=(0, 20), pady=(10, 10))
        
        # KD Ratio Label
        self.kd_ratio_label = self.create_label(
            kill_frame, text="KD Ratio: --", font=("Times New Roman", 12), fg="#00FFFF", bg="#484759"
        )
        self.kd_ratio_label.pack(side=tk.RIGHT, padx=(10, 10), pady=(10, 10))

        # Update the button to use the new combined function
        activate_load_key_button = self.create_button(
            key_frame, text="Activate & Load Key", font=("Times New Roman", 12), command=self.api.load_activate_key, bg="#000000", fg="#ffffff"
        )
        activate_load_key_button.pack(side=tk.LEFT, padx=(5, 0))

        # Options Frame
        options_frame = tk.Frame(self.app, bg="#484759")
        options_frame.pack(pady=(10, 10))

        # Commander Mode Button
        self.commander_mode_button = self.create_button(
            options_frame, text="Commander Mode", font=("Times New Roman", 12), command=self.cm.setup_commander_mode, bg="#000000", fg="#ffffff"
        )
        self.commander_mode_button.pack(side=tk.LEFT, pady=(10, 10))
        

        # App log text area
        self.log = AppLogger(self.setup_app_log_display())
        self.log.text_widget.pack(padx=10, pady=10)

        self.anonymize_button = self.create_button(
            options_frame, text=" Enable Anonymity ", font=("Times New Roman", 12), command=self.toggle_anonymize, bg="#000000", fg="#ffffff"
        )
        self.anonymize_button.pack(side=tk.LEFT, padx=(5, 0))

        self.debug_button = self.create_button(
            options_frame, text=" Enable Debug Mode ", font=("Times New Roman", 12), command=self.toggle_debug, bg="#000000", fg="#ffffff"
        )
        self.debug_button.pack(side=tk.RIGHT, padx=(5, 0), pady=(5, 5))
        
        # Volume Slider Frame
        volume_frame = tk.Frame(self.app, bg="#484759")
        volume_frame.pack(pady=(5, 10))

        volume_label = self.create_label(
            volume_frame, text="🔊 Volume", font=("Times New Roman", 12), fg="#ffffff", bg="#484759"
        )
        volume_label.pack(side=tk.LEFT, padx=(5, 10))

        volume_slider = tk.Scale(
            volume_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            length=200,
            bg="#484759",
            fg="#ffffff",
            troughcolor="#282a36",
            highlightbackground="#484759",
            command=lambda val: self.sounds.set_volume(int(val) / 100)
        )
        volume_slider.set(50)  # Default volume to 50%
        volume_slider.pack(side=tk.LEFT)


    def setup_gui(self, game_running):
        """Setup the GUI."""
        # Init setup
        try:
            self.app = tk.Tk(useTk=True)
            self.app.title(f"BlightVeil Kill Tracker v{self.local_version}")
            self.app.minsize(width=800, height=800)
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
                    self.app, text=update_message, font=("Times New Roman", 12), fg="#ff5555", bg="#484759", wraplength=700, justify="center", cursor="hand2"
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
            footer_text.pack(pady=5)
        except Exception as e:
            print(f"setup_gui(): Error rendering the footer: {e.__class__.__name__} {e}")
