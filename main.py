import customtkinter as ctk
from tkinter import messagebox
import requests
import os
import subprocess
import threading
import platform
import re
from pathlib import Path
import psutil
import time

class MinecraftServerManager(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window configuration
        self.title("ZCraft Panel")
        self.geometry("1100x750")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Server variables
        self.server_process = None
        self.server_folder = Path("minecraft_server")
        self.server_jar = None
        self.eula_accepted = False
        self.min_ram = 1
        self.max_ram = 2
        
        # Monitoring variables
        self.monitoring = False
        self.cpu_usage = 0
        self.ram_usage = 0
        self.players_online = 0
        self.tps = 20.0
        
        # Create server folder if it doesn't exist
        self.server_folder.mkdir(exist_ok=True)
        
        # Setup GUI
        self.setup_ui()
        
        # Check for existing EULA
        self.check_existing_eula()
        
    def setup_ui(self):
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar for navigation
        self.setup_sidebar()
        
        # Main content area
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        # Create content frames
        self.setup_content_frames()
        
        # Show dashboard by default
        self.show_frame("dashboard")
        
    def setup_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=("gray80", "gray20"))
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(8, weight=1)
        
        # Logo/Title
        title = ctk.CTkLabel(sidebar, text="🎮 ZCraft \nPanel", 
                           font=ctk.CTkFont(size=20, weight="bold"),
                           text_color=("#1f538d", "#3b8ed0"))
        title.grid(row=0, column=0, padx=20, pady=30)
        
        # Navigation buttons
        self.nav_buttons = {}
        nav_items = [
            ("📊 Dashboard", "dashboard"),
            ("⚙️ Setup", "setup"),
            ("🔧 Properties", "properties"),
            ("💻 Console", "console"),
            ("📈 Monitoring", "monitoring")
        ]
        
        for i, (text, frame_name) in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(sidebar, text=text, 
                              command=lambda f=frame_name: self.show_frame(f),
                              height=40,
                              font=ctk.CTkFont(size=13),
                              fg_color="transparent",
                              text_color=("gray10", "gray90"),
                              hover_color=("gray70", "gray30"),
                              anchor="w")
            btn.grid(row=i, column=0, padx=10, pady=5, sticky="ew")
            self.nav_buttons[frame_name] = btn
        
        # Theme toggle
        theme_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        theme_frame.grid(row=9, column=0, padx=20, pady=20, sticky="s")
        
        ctk.CTkLabel(theme_frame, text="Theme:", font=ctk.CTkFont(size=11)).pack()
        theme_switch = ctk.CTkSwitch(theme_frame, text="Dark Mode", 
                                    command=self.toggle_theme,
                                    onvalue="dark", offvalue="light")
        theme_switch.pack(pady=5)
        theme_switch.select()
        
    def setup_content_frames(self):
        self.frames = {}
        
        # Dashboard Frame
        self.frames["dashboard"] = self.create_dashboard_frame()
        
        # Setup Frame
        self.frames["setup"] = self.create_setup_frame()
        
        # Properties Frame
        self.frames["properties"] = self.create_properties_frame()
        
        # Console Frame
        self.frames["console"] = self.create_console_frame()
        
        # Monitoring Frame
        self.frames["monitoring"] = self.create_monitoring_frame()
        
    def create_dashboard_frame(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        frame.grid_columnconfigure((0, 1), weight=1)
        
        # Header
        header = ctk.CTkLabel(frame, text="🎮 Server Dashboard", 
                            font=ctk.CTkFont(size=28, weight="bold"))
        header.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="w")
        
        # Status Card
        status_card = ctk.CTkFrame(frame, height=120)
        status_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        status_card.grid_columnconfigure(1, weight=1)
        
        self.status_indicator = ctk.CTkLabel(status_card, text="●", 
                                            font=ctk.CTkFont(size=40),
                                            text_color="red")
        self.status_indicator.grid(row=0, column=0, rowspan=2, padx=20)
        
        self.status_text = ctk.CTkLabel(status_card, text="Server Offline", 
                                       font=ctk.CTkFont(size=20, weight="bold"),
                                       anchor="w")
        self.status_text.grid(row=0, column=1, sticky="w", pady=(20, 0))
        
        self.status_subtext = ctk.CTkLabel(status_card, text="Click 'Start Server' to begin", 
                                          font=ctk.CTkFont(size=12),
                                          text_color="gray",
                                          anchor="w")
        self.status_subtext.grid(row=1, column=1, sticky="w", pady=(0, 20))
        
        # Quick Stats Row
        stats_frame = ctk.CTkFrame(frame, fg_color="transparent")
        stats_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        # CPU Card
        cpu_card = self.create_stat_card(stats_frame, "💻 CPU", "0%", "Processor usage")
        cpu_card.grid(row=0, column=0, padx=5, sticky="ew")
        self.cpu_label = cpu_card.winfo_children()[1]
        
        # RAM Card
        ram_card = self.create_stat_card(stats_frame, "🧠 RAM", "0 MB", "Memory usage")
        ram_card.grid(row=0, column=1, padx=5, sticky="ew")
        self.ram_label = ram_card.winfo_children()[1]
        
        # Players Card
        players_card = self.create_stat_card(stats_frame, "👥 Players", "0", "Online players")
        players_card.grid(row=0, column=2, padx=5, sticky="ew")
        self.players_label = players_card.winfo_children()[1]
        
        # TPS Card
        tps_card = self.create_stat_card(stats_frame, "⚡ TPS", "20.0", "Ticks per second")
        tps_card.grid(row=0, column=3, padx=5, sticky="ew")
        self.tps_label = tps_card.winfo_children()[1]
        
        # Control Buttons
        control_frame = ctk.CTkFrame(frame, fg_color="transparent")
        control_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        control_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.dash_start_btn = ctk.CTkButton(control_frame, text="▶ Start Server", 
                                           command=self.start_server,
                                           height=50,
                                           font=ctk.CTkFont(size=16, weight="bold"),
                                           fg_color=("green", "#006400"),
                                           hover_color=("darkgreen", "#004d00"))
        self.dash_start_btn.grid(row=0, column=0, padx=5, sticky="ew")
        
        self.dash_stop_btn = ctk.CTkButton(control_frame, text="⏹ Stop Server",
                                          command=self.stop_server,
                                          height=50,
                                          font=ctk.CTkFont(size=16, weight="bold"),
                                          fg_color=("red", "#8b0000"),
                                          hover_color=("darkred", "#660000"),
                                          state="disabled")
        self.dash_stop_btn.grid(row=0, column=1, padx=5, sticky="ew")
        
        # Quick Actions
        actions_label = ctk.CTkLabel(frame, text="⚡ Quick Actions", 
                                    font=ctk.CTkFont(size=18, weight="bold"))
        actions_label.grid(row=4, column=0, columnspan=2, pady=(10, 10), sticky="w")
        
        actions_frame = ctk.CTkFrame(frame)
        actions_frame.grid(row=5, column=0, columnspan=2, sticky="ew")
        actions_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        ctk.CTkButton(actions_frame, text="📂 Open Folder", 
                     command=self.open_server_folder,
                     height=40).grid(row=0, column=0, padx=5, pady=10, sticky="ew")
        
        ctk.CTkButton(actions_frame, text="🔄 Restart Server",
                     command=self.restart_server,
                     height=40).grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        
        ctk.CTkButton(actions_frame, text="💾 Backup World",
                     command=self.backup_world,
                     height=40).grid(row=0, column=2, padx=5, pady=10, sticky="ew")
        
        return frame
        
    def create_stat_card(self, parent, title, value, subtitle):
        card = ctk.CTkFrame(parent, height=100)
        card.grid_propagate(False)
        
        ctk.CTkLabel(card, text=title, 
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color="gray").pack(pady=(10, 0))
        
        value_label = ctk.CTkLabel(card, text=value, 
                                  font=ctk.CTkFont(size=24, weight="bold"))
        value_label.pack(pady=5)
        
        ctk.CTkLabel(card, text=subtitle, 
                    font=ctk.CTkFont(size=10),
                    text_color="gray").pack(pady=(0, 10))
        
        return card
        
    def create_setup_frame(self):
        frame = ctk.CTkScrollableFrame(self.main_frame)
        
        # Header
        header = ctk.CTkLabel(frame, text="⚙️ Server Setup", 
                            font=ctk.CTkFont(size=28, weight="bold"))
        header.pack(pady=(0, 20), anchor="w")
        
        # EULA Section
        eula_frame = ctk.CTkFrame(frame, fg_color=("gray85", "gray25"))
        eula_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(eula_frame, text="⚠️ EULA Agreement Required", 
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=("red", "orange")).pack(pady=(15, 10))
        
        eula_text = ctk.CTkTextbox(eula_frame, height=80)
        eula_text.pack(pady=10, padx=20, fill="x")
        eula_text.insert("1.0", """By running a Minecraft server, you agree to:
• Own a legitimate copy of Minecraft
• Follow the Microsoft Services Agreement
• Read and accept the EULA at: https://aka.ms/MinecraftEULA""")
        eula_text.configure(state="disabled")
        
        self.eula_var = ctk.BooleanVar(value=self.eula_accepted)
        self.eula_check = ctk.CTkCheckBox(eula_frame, 
                                         text="✓ I have read and agree to the Minecraft EULA", 
                                         variable=self.eula_var,
                                         command=self.on_eula_change,
                                         font=ctk.CTkFont(size=14, weight="bold"))
        self.eula_check.pack(pady=15)
        
        # RAM Configuration
        ram_frame = ctk.CTkFrame(frame)
        ram_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(ram_frame, text="💾 Memory Allocation", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 10), anchor="w", padx=15)
        
        # Get system RAM
        total_ram = psutil.virtual_memory().total / (1024**3)
        
        ram_info = ctk.CTkLabel(ram_frame, 
                               text=f"System RAM: {total_ram:.1f} GB | Recommended: 2-4 GB for small servers",
                               font=ctk.CTkFont(size=11),
                               text_color="gray")
        ram_info.pack(padx=15, anchor="w")
        
        # Min RAM
        min_ram_frame = ctk.CTkFrame(ram_frame, fg_color="transparent")
        min_ram_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(min_ram_frame, text="Minimum RAM (GB):", width=150).pack(side="left", padx=5)
        self.min_ram_slider = ctk.CTkSlider(min_ram_frame, from_=1, to=16, number_of_steps=15,
                                           command=self.update_min_ram)
        self.min_ram_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.min_ram_slider.set(self.min_ram)
        
        self.min_ram_label = ctk.CTkLabel(min_ram_frame, text=f"{self.min_ram} GB", width=60)
        self.min_ram_label.pack(side="left", padx=5)
        
        # Max RAM
        max_ram_frame = ctk.CTkFrame(ram_frame, fg_color="transparent")
        max_ram_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkLabel(max_ram_frame, text="Maximum RAM (GB):", width=150).pack(side="left", padx=5)
        self.max_ram_slider = ctk.CTkSlider(max_ram_frame, from_=1, to=16, number_of_steps=15,
                                           command=self.update_max_ram)
        self.max_ram_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.max_ram_slider.set(self.max_ram)
        
        self.max_ram_label = ctk.CTkLabel(max_ram_frame, text=f"{self.max_ram} GB", width=60)
        self.max_ram_label.pack(side="left", padx=5)
        
        # Server Configuration
        config_frame = ctk.CTkFrame(frame)
        config_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(config_frame, text="🎮 Server Configuration", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 10), anchor="w", padx=15)
        
        # Server Type
        type_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        type_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(type_frame, text="Server Type:", width=120).pack(side="left", padx=5)
        
        self.server_type = ctk.StringVar(value="Vanilla")
        type_options = ctk.CTkFrame(type_frame, fg_color="transparent")
        type_options.pack(side="left", fill="x", expand=True)
        
        for server_type in ["Vanilla", "Paper", "Forge", "Fabric"]:
            ctk.CTkRadioButton(type_options, text=server_type, 
                              variable=self.server_type, 
                              value=server_type).pack(side="left", padx=10)
        
        # Version
        version_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        version_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(version_frame, text="Version:", width=120).pack(side="left", padx=5)
        
        self.version_combo = ctk.CTkComboBox(version_frame, values=["Loading..."], state="readonly")
        self.version_combo.pack(side="left", padx=5, fill="x", expand=True)
        
        ctk.CTkButton(version_frame, text="🔄 Refresh", 
                     command=self.load_versions, width=100).pack(side="left", padx=5)
        
        # Load versions
        threading.Thread(target=self.load_versions, daemon=True).start()
        
        # Download Button
        self.download_btn = ctk.CTkButton(frame, text="📥 Download Server", 
                                         command=self.download_server,
                                         height=50,
                                         font=ctk.CTkFont(size=16, weight="bold"),
                                         fg_color=("green", "#006400"),
                                         hover_color=("darkgreen", "#004d00"))
        self.download_btn.pack(fill="x", pady=20, padx=15)
        
        # Status
        self.status_label = ctk.CTkLabel(frame, text="Ready to download", 
                                        font=ctk.CTkFont(size=13))
        self.status_label.pack(pady=10)
        
        return frame
        
    def create_properties_frame(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # Header with buttons
        header_frame = ctk.CTkFrame(frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        header_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(header_frame, text="🔧 Server Properties", 
                    font=ctk.CTkFont(size=28, weight="bold")).grid(row=0, column=0, sticky="w")
        
        button_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        button_frame.grid(row=0, column=1, sticky="e")
        
        ctk.CTkButton(button_frame, text="📂 Load", command=self.load_properties, width=100).pack(side="left", padx=2)
        ctk.CTkButton(button_frame, text="💾 Save", command=self.save_properties, width=100).pack(side="left", padx=2)
        ctk.CTkButton(button_frame, text="🔄 Reset", command=self.reset_properties, width=100,
                     fg_color="orange", hover_color="darkorange").pack(side="left", padx=2)
        
        # Scrollable properties
        scroll_frame = ctk.CTkScrollableFrame(frame)
        scroll_frame.grid(row=1, column=0, sticky="nsew")
        
        self.properties = {}
        
        # Add property categories
        categories = [
            ("🎮 Basic Settings", [
                ("motd", "Server MOTD", "A Minecraft Server"),
                ("server-port", "Server Port", "25565"),
                ("max-players", "Max Players", "20"),
                ("online-mode", "Online Mode", "true"),
                ("white-list", "Whitelist", "false"),
            ]),
            ("🌍 World Settings", [
                ("level-name", "World Name", "world"),
                ("level-seed", "Seed", ""),
                ("gamemode", "Game Mode", "survival"),
                ("difficulty", "Difficulty", "normal"),
                ("pvp", "PVP", "true"),
                ("spawn-protection", "Spawn Protection", "16"),
            ]),
            ("⚡ Performance", [
                ("view-distance", "View Distance", "10"),
                ("simulation-distance", "Simulation Distance", "10"),
                ("max-tick-time", "Max Tick Time", "60000"),
            ])
        ]
        
        for category_name, props in categories:
            self.add_category(scroll_frame, category_name)
            self.add_properties(scroll_frame, props)
        
        return frame
        
    def create_console_frame(self):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # Header with control buttons
        header_frame = ctk.CTkFrame(frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        header_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(header_frame, text="💻 Server Console", 
                    font=ctk.CTkFont(size=28, weight="bold")).grid(row=0, column=0, sticky="w")
        
        control_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        control_frame.grid(row=0, column=1, sticky="e")
        
        self.console_start_btn = ctk.CTkButton(control_frame, text="▶ Start", 
                                              command=self.start_server,
                                              width=100,
                                              fg_color="green", hover_color="darkgreen")
        self.console_start_btn.pack(side="left", padx=2)
        
        self.console_stop_btn = ctk.CTkButton(control_frame, text="⏹ Stop",
                                             command=self.stop_server,
                                             width=100,
                                             fg_color="red", hover_color="darkred",
                                             state="disabled")
        self.console_stop_btn.pack(side="left", padx=2)
        
        ctk.CTkButton(control_frame, text="🗑️ Clear", 
                     command=self.clear_console, width=100).pack(side="left", padx=2)
        
        # Console output
        self.console_output = ctk.CTkTextbox(frame, wrap="word", 
                                            font=("Consolas", 11),
                                            fg_color=("gray95", "gray15"))
        self.console_output.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        
        # Command input
        input_frame = ctk.CTkFrame(frame, fg_color="transparent")
        input_frame.grid(row=2, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)
        
        self.command_entry = ctk.CTkEntry(input_frame, 
                                         placeholder_text="Enter server command...",
                                         height=40,
                                         font=ctk.CTkFont(size=13))
        self.command_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.command_entry.bind("<Return>", lambda e: self.send_command())
        
        ctk.CTkButton(input_frame, text="Send ➤", 
                     command=self.send_command,
                     height=40, width=100,
                     font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=1)
        
        return frame
        
    def create_monitoring_frame(self):
        frame = ctk.CTkScrollableFrame(self.main_frame)
        
        # Header
        header = ctk.CTkLabel(frame, text="📈 Performance Monitoring", 
                            font=ctk.CTkFont(size=28, weight="bold"))
        header.pack(pady=(0, 20), anchor="w")
        
        # Real-time stats
        stats_container = ctk.CTkFrame(frame)
        stats_container.pack(fill="x", pady=(0, 20))
        
        # CPU Usage
        cpu_frame = ctk.CTkFrame(stats_container)
        cpu_frame.pack(fill="x", padx=15, pady=10)
        
        cpu_header = ctk.CTkFrame(cpu_frame, fg_color="transparent")
        cpu_header.pack(fill="x", pady=(10, 5))
        
        ctk.CTkLabel(cpu_header, text="💻 CPU Usage", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=10)
        self.mon_cpu_label = ctk.CTkLabel(cpu_header, text="0%", 
                                         font=ctk.CTkFont(size=16, weight="bold"),
                                         text_color=("green", "lightgreen"))
        self.mon_cpu_label.pack(side="right", padx=10)
        
        self.cpu_progress = ctk.CTkProgressBar(cpu_frame, height=20)
        self.cpu_progress.pack(fill="x", padx=15, pady=(0, 10))
        self.cpu_progress.set(0)
        
        # RAM Usage
        ram_frame = ctk.CTkFrame(stats_container)
        ram_frame.pack(fill="x", padx=15, pady=10)
        
        ram_header = ctk.CTkFrame(ram_frame, fg_color="transparent")
        ram_header.pack(fill="x", pady=(10, 5))
        
        ctk.CTkLabel(ram_header, text="🧠 Memory Usage", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=10)
        self.mon_ram_label = ctk.CTkLabel(ram_header, text="0 MB", 
                                         font=ctk.CTkFont(size=16, weight="bold"),
                                         text_color=("blue", "lightblue"))
        self.mon_ram_label.pack(side="right", padx=10)
        
        self.ram_progress = ctk.CTkProgressBar(ram_frame, height=20)
        self.ram_progress.pack(fill="x", padx=15, pady=(0, 10))
        self.ram_progress.set(0)
        
        # Server Stats
        server_stats_frame = ctk.CTkFrame(frame)
        server_stats_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(server_stats_frame, text="🎮 Server Statistics", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 10), padx=15, anchor="w")
        
        # Players Online
        players_stat = ctk.CTkFrame(server_stats_frame, fg_color="transparent")
        players_stat.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(players_stat, text="👥 Players Online:", width=150).pack(side="left", padx=5)
        self.mon_players_label = ctk.CTkLabel(players_stat, text="0", 
                                             font=ctk.CTkFont(size=16, weight="bold"))
        self.mon_players_label.pack(side="left", padx=5)
        
        # TPS
        tps_stat = ctk.CTkFrame(server_stats_frame, fg_color="transparent")
        tps_stat.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(tps_stat, text="⚡ TPS (Ticks/Second):", width=150).pack(side="left", padx=5)
        self.mon_tps_label = ctk.CTkLabel(tps_stat, text="20.0", 
                                         font=ctk.CTkFont(size=16, weight="bold"),
                                         text_color=("green", "lightgreen"))
        self.mon_tps_label.pack(side="left", padx=5)
        
        # Uptime
        uptime_stat = ctk.CTkFrame(server_stats_frame, fg_color="transparent")
        uptime_stat.pack(fill="x", padx=15, pady=(5, 15))
        
        ctk.CTkLabel(uptime_stat, text="⏱️ Uptime:", width=150).pack(side="left", padx=5)
        self.mon_uptime_label = ctk.CTkLabel(uptime_stat, text="0h 0m 0s",
                                               font=ctk.CTkFont(size=16, weight="bold"))
        self.mon_uptime_label.pack(side="left", padx=5)
        
        # Auto-refresh toggle
        refresh_frame = ctk.CTkFrame(frame)
        refresh_frame.pack(fill="x", pady=20)
        
        ctk.CTkLabel(refresh_frame, text="⚙️ Monitoring Settings", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 10), padx=15, anchor="w")
        
        auto_refresh = ctk.CTkSwitch(refresh_frame, text="Auto-refresh (Updates every 2 seconds)",
                                    command=self.toggle_monitoring,
                                    font=ctk.CTkFont(size=13))
        auto_refresh.pack(padx=15, pady=(0, 15), anchor="w")
        
        return frame
    
    def show_frame(self, frame_name):
        # Hide all frames
        for frame in self.frames.values():
            frame.grid_remove()
        
        # Show selected frame
        self.frames[frame_name].grid(row=0, column=0, sticky="nsew")
        
        # Update navigation buttons
        for name, btn in self.nav_buttons.items():
            if name == frame_name:
                btn.configure(fg_color=("gray70", "gray30"))
            else:
                btn.configure(fg_color="transparent")
    
    def toggle_theme(self):
        current = ctk.get_appearance_mode()
        new_mode = "light" if current == "Dark" else "dark"
        ctk.set_appearance_mode(new_mode)
    
    def update_min_ram(self, value):
        self.min_ram = int(value)
        self.min_ram_label.configure(text=f"{self.min_ram} GB")
        if self.min_ram > self.max_ram:
            self.max_ram = self.min_ram
            self.max_ram_slider.set(self.max_ram)
            self.max_ram_label.configure(text=f"{self.max_ram} GB")
    
    def update_max_ram(self, value):
        self.max_ram = int(value)
        self.max_ram_label.configure(text=f"{self.max_ram} GB")
        if self.max_ram < self.min_ram:
            self.min_ram = self.max_ram
            self.min_ram_slider.set(self.min_ram)
            self.min_ram_label.configure(text=f"{self.min_ram} GB")
    
    def toggle_monitoring(self):
        self.monitoring = not self.monitoring
        if self.monitoring:
            threading.Thread(target=self.monitor_server, daemon=True).start()
    
    def monitor_server(self):
        self.server_start_time = time.time()
        
        while self.monitoring:
            if self.server_process and self.server_process.poll() is None:
                try:
                    # Get process info
                    proc = psutil.Process(self.server_process.pid)
                    
                    # CPU usage
                    self.cpu_usage = proc.cpu_percent(interval=0.5)
                    
                    # RAM usage
                    mem_info = proc.memory_info()
                    self.ram_usage = mem_info.rss / (1024 * 1024)  # Convert to MB
                    
                    # Calculate uptime
                    uptime_seconds = int(time.time() - self.server_start_time)
                    hours = uptime_seconds // 3600
                    minutes = (uptime_seconds % 3600) // 60
                    seconds = uptime_seconds % 60
                    
                    # Update UI
                    self.after(0, self.update_monitoring_ui, hours, minutes, seconds)
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            else:
                # Server not running
                self.after(0, self.reset_monitoring_ui)
            
            time.sleep(2)
    
    def update_monitoring_ui(self, hours, minutes, seconds):
        # Update dashboard
        self.cpu_label.configure(text=f"{self.cpu_usage:.1f}%")
        self.ram_label.configure(text=f"{self.ram_usage:.0f} MB")
        self.players_label.configure(text=str(self.players_online))
        self.tps_label.configure(text=f"{self.tps:.1f}")
        
        # Update monitoring page
        self.mon_cpu_label.configure(text=f"{self.cpu_usage:.1f}%")
        self.cpu_progress.set(min(self.cpu_usage / 100, 1.0))
        
        ram_percent = min(self.ram_usage / (self.max_ram * 1024), 1.0)
        self.mon_ram_label.configure(text=f"{self.ram_usage:.0f} MB / {self.max_ram * 1024} MB")
        self.ram_progress.set(ram_percent)
        
        self.mon_players_label.configure(text=str(self.players_online))
        self.mon_tps_label.configure(text=f"{self.tps:.1f}")
        
        # Color code TPS
        if self.tps >= 19:
            color = ("green", "lightgreen")
        elif self.tps >= 15:
            color = ("orange", "yellow")
        else:
            color = ("red", "salmon")
        self.mon_tps_label.configure(text_color=color)
        self.tps_label.configure(text_color=color)
        
        # Update uptime
        self.mon_uptime_label.configure(text=f"{hours}h {minutes}m {seconds}s")
    
    def reset_monitoring_ui(self):
        self.cpu_label.configure(text="0%")
        self.ram_label.configure(text="0 MB")
        self.players_label.configure(text="0")
        self.tps_label.configure(text="20.0")
        
        self.mon_cpu_label.configure(text="0%")
        self.cpu_progress.set(0)
        self.mon_ram_label.configure(text="0 MB")
        self.ram_progress.set(0)
        self.mon_players_label.configure(text="0")
        self.mon_tps_label.configure(text="20.0")
        self.mon_uptime_label.configure(text="0h 0m 0s")
    
    def check_existing_eula(self):
        eula_path = self.server_folder / "eula.txt"
        if eula_path.exists():
            with open(eula_path, 'r') as f:
                content = f.read()
                if "eula=true" in content:
                    self.eula_accepted = True
                    self.eula_var.set(True)
    
    def on_eula_change(self):
        self.eula_accepted = self.eula_var.get()
        if self.eula_accepted:
            self.write_eula()
    
    def write_eula(self):
        eula_path = self.server_folder / "eula.txt"
        with open(eula_path, 'w') as f:
            f.write("#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://aka.ms/MinecraftEULA).\n")
            f.write(f"eula={'true' if self.eula_accepted else 'false'}\n")
        self.update_status("✓ EULA accepted and saved!")
    
    def load_versions(self):
        try:
            self.after(0, lambda: self.update_status("Loading versions..."))
            
            server_type = self.server_type.get()
            versions = []
            
            if server_type == "Vanilla":
                manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
                response = requests.get(manifest_url, timeout=10)
                manifest = response.json()
                versions = [v['id'] for v in manifest['versions'] if v['type'] == 'release']
                
            elif server_type == "Paper":
                try:
                    response = requests.get("https://api.papermc.io/v2/projects/paper", timeout=10)
                    versions = response.json()['versions']
                    versions.reverse()
                except:
                    versions = ["1.20.4", "1.20.2", "1.20.1", "1.19.4"]
                    
            elif server_type == "Fabric":
                try:
                    response = requests.get("https://meta.fabricmc.net/v2/versions/game", timeout=10)
                    data = response.json()
                    versions = [v['version'] for v in data if v['stable']]
                except:
                    versions = ["1.20.4", "1.20.2", "1.20.1", "1.19.4"]
                    
            elif server_type == "Forge":
                versions = ["1.20.1", "1.19.4", "1.19.3", "1.19.2", "1.18.2", "1.16.5"]
            
            if versions:
                self.after(0, lambda v=versions: self.version_combo.configure(values=v))
                self.after(0, lambda v=versions: self.version_combo.set(v[0]))
                self.after(0, lambda: self.update_status(f"Loaded {len(versions)} versions"))
            else:
                self.after(0, lambda: self.update_status("Failed to load versions"))
                
        except Exception as e:
            print(f"Error loading versions: {e}")
            self.after(0, lambda: self.update_status(f"Error: {str(e)}"))
    
    def update_status(self, message):
        self.status_label.configure(text=message)
    
    def download_server(self):
        if not self.eula_accepted:
            messagebox.showerror("EULA Required", 
                "⚠️ You must accept the Minecraft EULA first!")
            return
            
        server_type = self.server_type.get()
        version = self.version_combo.get()
        
        if not version or version == "Loading...":
            messagebox.showerror("Error", "Please select a Minecraft version!")
            return
            
        self.download_btn.configure(state="disabled")
        self.update_status(f"Downloading {server_type} {version}...")
        
        thread = threading.Thread(target=self._download_thread, args=(server_type, version))
        thread.daemon = True
        thread.start()
    
    def _download_thread(self, server_type, version):
        try:
            if server_type == "Vanilla":
                success = self.download_vanilla(version)
            elif server_type == "Paper":
                success = self.download_paper(version)
            elif server_type == "Forge":
                success = self.download_forge(version)
            elif server_type == "Fabric":
                success = self.download_fabric(version)
            
            if success:
                self.create_start_scripts()
                self.after(0, lambda: self.update_status(f"✓ {server_type} {version} downloaded!"))
                self.after(0, lambda: messagebox.showinfo("Success", "Server downloaded successfully!"))
            else:
                self.after(0, lambda: self.update_status("✗ Download failed!"))
        except Exception as e:
            self.after(0, lambda: self.update_status(f"Error: {str(e)}"))
            self.after(0, lambda: messagebox.showerror("Error", f"Download failed: {str(e)}"))
        finally:
            self.after(0, lambda: self.download_btn.configure(state="normal"))
    
    def download_vanilla(self, version):
        try:
            manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
            manifest = requests.get(manifest_url).json()
            
            version_data = None
            for v in manifest['versions']:
                if v['id'] == version:
                    version_data = v
                    break
            
            if not version_data:
                raise Exception(f"Version {version} not found!")
            
            version_url = version_data['url']
            version_info = requests.get(version_url).json()
            server_url = version_info['downloads']['server']['url']
            jar_path = self.server_folder / "server.jar"
            
            response = requests.get(server_url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(jar_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress = (downloaded / total_size) * 100 if total_size > 0 else 0
                    self.after(0, lambda p=progress: self.update_status(f"Downloading... {p:.1f}%"))
            
            self.server_jar = jar_path
            return True
        except Exception as e:
            print(f"Vanilla download error: {e}")
            return False
    
    def download_paper(self, version):
        try:
            api_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}"
            response = requests.get(api_url)
            
            if response.status_code != 200:
                raise Exception(f"Paper version {version} not found!")
            
            builds = response.json()['builds']
            latest_build = builds[-1]
            
            download_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{latest_build}/downloads/paper-{version}-{latest_build}.jar"
            jar_path = self.server_folder / "server.jar"
            
            response = requests.get(download_url, stream=True)
            with open(jar_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.server_jar = jar_path
            return True
        except Exception as e:
            print(f"Paper download error: {e}")
            return False
    
    def download_forge(self, version):
        self.after(0, lambda: messagebox.showinfo("Forge", 
            f"Please download Forge {version} installer from:\nhttps://files.minecraftforge.net/"))
        return False
    
    def download_fabric(self, version):
        try:
            installer_url = "https://maven.fabricmc.net/net/fabricmc/fabric-installer/0.11.2/fabric-installer-0.11.2.jar"
            installer_path = self.server_folder / "fabric-installer.jar"
            
            response = requests.get(installer_url)
            with open(installer_path, 'wb') as f:
                f.write(response.content)
            
            result = subprocess.run([
                "java", "-jar", str(installer_path),
                "server", "-mcversion", version, "-dir", str(self.server_folder)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.server_jar = self.server_folder / "fabric-server-launch.jar"
                return True
            return False
        except Exception as e:
            print(f"Fabric download error: {e}")
            return False
    
    def create_start_scripts(self):
        bat_content = f'@echo off\njava -Xmx{self.max_ram}G -Xms{self.min_ram}G -jar server.jar nogui\npause'
        with open(self.server_folder / "start.bat", 'w') as f:
            f.write(bat_content)
        
        sh_content = f'#!/bin/bash\njava -Xmx{self.max_ram}G -Xms{self.min_ram}G -jar server.jar nogui'
        sh_path = self.server_folder / "start.sh"
        with open(sh_path, 'w') as f:
            f.write(sh_content)
        os.chmod(sh_path, 0o755)
    
    def add_category(self, parent, title):
        frame = ctk.CTkFrame(parent, fg_color=("gray70", "gray30"))
        frame.pack(fill="x", pady=(10, 2), padx=5)
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=13, weight="bold")).pack(pady=5, padx=10, anchor="w")
    
    def add_properties(self, parent, props_list):
        for key, label, default in props_list:
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.pack(fill="x", pady=2, padx=5)
            
            ctk.CTkLabel(frame, text=label, width=180, anchor="w").pack(side="left", padx=5)
            entry = ctk.CTkEntry(frame, width=300)
            entry.pack(side="left", padx=5, fill="x", expand=True)
            entry.insert(0, default)
            self.properties[key] = entry
    
    def load_properties(self):
        props_path = self.server_folder / "server.properties"
        if not props_path.exists():
            messagebox.showinfo("Info", "No server.properties file found.")
            return
        
        with open(props_path, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    if key in self.properties:
                        self.properties[key].delete(0, 'end')
                        self.properties[key].insert(0, value)
        
        messagebox.showinfo("Success", "Properties loaded!")
    
    def save_properties(self):
        props_path = self.server_folder / "server.properties"
        
        with open(props_path, 'w') as f:
            f.write("#Minecraft server properties\n")
            for key, entry in self.properties.items():
                f.write(f"{key}={entry.get()}\n")
        
        messagebox.showinfo("Success", "Properties saved!")
    
    def reset_properties(self):
        result = messagebox.askyesno("Reset Properties", 
            "Reset all properties to default values?")
        
        if result:
            defaults = {
                "motd": "A Minecraft Server",
                "server-port": "25565",
                "max-players": "20",
                "online-mode": "true",
                "white-list": "false",
                "level-name": "world",
                "level-seed": "",
                "gamemode": "survival",
                "difficulty": "normal",
                "pvp": "true",
                "spawn-protection": "16",
                "view-distance": "10",
                "simulation-distance": "10",
                "max-tick-time": "60000",
            }
            
            for key, entry in self.properties.items():
                if key in defaults:
                    entry.delete(0, 'end')
                    entry.insert(0, defaults[key])
            
            messagebox.showinfo("Success", "Properties reset!")
    
    def start_server(self):
        if not self.server_jar or not self.server_jar.exists():
            jar_path = self.server_folder / "server.jar"
            if jar_path.exists():
                self.server_jar = jar_path
            else:
                messagebox.showerror("Error", "Server jar not found! Download a server first.")
                return
        
        if not self.eula_accepted:
            messagebox.showerror("EULA Required", "You must accept the EULA first!")
            return
        
        try:
            self.console_output.delete("1.0", "end")
            self.console_output.insert("end", "Starting server...\n")
            
            if platform.system() == "Windows":
                self.server_process = subprocess.Popen(
                    ["java", f"-Xmx{self.max_ram}G", f"-Xms{self.min_ram}G", "-jar", "server.jar", "nogui"],
                    cwd=str(self.server_folder),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                self.server_process = subprocess.Popen(
                    ["java", f"-Xmx{self.max_ram}G", f"-Xms{self.min_ram}G", "-jar", "server.jar", "nogui"],
                    cwd=str(self.server_folder),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
            
            # Update all start/stop buttons
            self.dash_start_btn.configure(state="disabled")
            self.dash_stop_btn.configure(state="normal")
            self.console_start_btn.configure(state="disabled")
            self.console_stop_btn.configure(state="normal")
            
            # Update status
            self.status_indicator.configure(text_color="green")
            self.status_text.configure(text="Server Online")
            self.status_subtext.configure(text="Server is running...")
            
            # Start monitoring
            if not self.monitoring:
                self.monitoring = True
                threading.Thread(target=self.monitor_server, daemon=True).start()
            
            # Start output reader
            threading.Thread(target=self.read_server_output, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {str(e)}")
            self.console_output.insert("end", f"\nError: {str(e)}\n")
    
    def stop_server(self):
        if self.server_process:
            try:
                self.console_output.insert("end", "\nStopping server...\n")
                self.server_process.stdin.write("stop\n")
                self.server_process.stdin.flush()
                threading.Thread(target=self.wait_for_stop, daemon=True).start()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to stop server: {str(e)}")
    
    def wait_for_stop(self):
        if self.server_process:
            self.server_process.wait()
            self.after(0, self.on_server_stopped)
    
    def on_server_stopped(self):
        self.console_output.insert("end", "\nServer stopped.\n")
        
        # Update all buttons
        self.dash_start_btn.configure(state="normal")
        self.dash_stop_btn.configure(state="disabled")
        self.console_start_btn.configure(state="normal")
        self.console_stop_btn.configure(state="disabled")
        
        # Update status
        self.status_indicator.configure(text_color="red")
        self.status_text.configure(text="Server Offline")
        self.status_subtext.configure(text="Click 'Start Server' to begin")
        
        self.server_process = None
    
    def read_server_output(self):
        if not self.server_process:
            return
        
        try:
            for line in iter(self.server_process.stdout.readline, ''):
                if line:
                    self.after(0, lambda l=line: self.console_output.insert("end", l))
                    self.after(0, lambda: self.console_output.see("end"))
                    
                    # Parse for player count and TPS
                    self.parse_server_output(line)
                
                if self.server_process.poll() is not None:
                    break
        except Exception as e:
            print(f"Error reading output: {e}")
        
        self.after(0, self.on_server_stopped)
    
    def parse_server_output(self, line):
        # Parse player join/leave
        if "joined the game" in line.lower():
            self.players_online += 1
        elif "left the game" in line.lower():
            self.players_online = max(0, self.players_online - 1)
        
        # Parse TPS from server output (if available)
        tps_match = re.search(r'TPS.*?(\d+\.?\d*)', line, re.IGNORECASE)
        if tps_match:
            try:
                self.tps = float(tps_match.group(1))
            except:
                pass
    
    def send_command(self):
        if not self.server_process:
            messagebox.showwarning("Warning", "Server is not running!")
            return
        
        command = self.command_entry.get().strip()
        if command:
            try:
                self.server_process.stdin.write(command + "\n")
                self.server_process.stdin.flush()
                self.console_output.insert("end", f"> {command}\n")
                self.command_entry.delete(0, 'end')
            except Exception as e:
                messagebox.showerror("Error", f"Failed to send command: {str(e)}")
    
    def clear_console(self):
        self.console_output.delete("1.0", "end")
    
    def open_server_folder(self):
        if platform.system() == "Windows":
            os.startfile(self.server_folder)
        elif platform.system() == "Darwin":
            subprocess.run(["open", str(self.server_folder)])
        else:
            subprocess.run(["xdg-open", str(self.server_folder)])
    
    def restart_server(self):
        if self.server_process:
            self.stop_server()
            self.after(3000, self.start_server)
        else:
            messagebox.showinfo("Info", "Server is not running!")
    
    def backup_world(self):
        messagebox.showinfo("Backup", "Backup feature coming soon!\n\nFor now, manually copy the 'world' folder in the server directory.")


def main():
    try:
        app = MinecraftServerManager()
        app.mainloop()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()