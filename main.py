import sys
import os
import subprocess
import json
import ctypes
import argparse
import urllib.request
import shutil
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLineEdit, QLabel, QFileDialog, QMessageBox, 
                            QStackedWidget, QTextBrowser, QProgressDialog)
from PyQt6.QtCore import Qt, QProcess, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPalette, QBrush, QPainter, QImage

# Get the application base directory (works for both script and frozen exe)
def get_base_dir():
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle (compiled with PyInstaller)
        return os.path.dirname(sys.executable)
    else:
        # If the application is run as a script
        return os.path.dirname(os.path.abspath(__file__))

# Check and download resource files if missing
def check_and_download_resources():
    base_dir = get_base_dir()
    resources_dir = os.path.join(base_dir, "iw9x", "res")
    
    # Create resources directory if it doesn't exist
    os.makedirs(resources_dir, exist_ok=True)
    
    # List of resource files to check
    resource_files = ["info.png", "home.png", "settings.png"]
    base_url = "https://mot204t.github.io/iw9x/github/iw9x/res/"
    
    for resource_file in resource_files:
        file_path = os.path.join(resources_dir, resource_file)
        
        # If the file doesn't exist, download it
        if not os.path.exists(file_path):
            try:
                print(f"Downloading missing resource: {resource_file}")
                url = f"{base_url}{resource_file}"
                
                # Create a request with browser-like headers
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive',
                    'Cache-Control': 'max-age=0'
                }
                
                request = urllib.request.Request(url, headers=headers)
                
                # Download the file
                with urllib.request.urlopen(request) as response, open(file_path, 'wb') as out_file:
                    out_file.write(response.read())
                    
                print(f"Downloaded {resource_file} successfully")
            except Exception as e:
                print(f"Failed to download {resource_file}: {str(e)}")

# Check if the application is running with admin privileges
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# Restart the application with admin privileges
def run_as_admin():
    try:
        if getattr(sys, 'frozen', False):
            # If the application is run as a bundle (compiled with PyInstaller)
            executable = sys.executable
            arguments = []  # No arguments needed, the executable itself contains everything
        else:
            # If the application is run as a script
            executable = sys.executable
            arguments = [os.path.abspath(sys.argv[0])] + sys.argv[1:]
            
        # Use ShellExecuteW to run the application with admin privileges
        ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, " ".join(arguments), None, 1)
    except Exception as e:
        print(f"Error elevating privileges: {e}")

# Check if a service is running
def is_service_running(service_name):
    try:
        # Use sc query to check if service is running
        result = subprocess.run(f'sc query {service_name}', shell=True, capture_output=True, text=True)
        # Check if the service exists and is running
        return "RUNNING" in result.stdout
    except Exception:
        return False

# Load settings from the settings file
def load_settings():
    base_dir = get_base_dir()
    settings_file = os.path.join(base_dir, "settings.json")
    game_path = ""
    
    try:
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                game_path = settings.get('game_path', '')
    except Exception as e:
        print(f"Error loading settings: {e}")
        
    return game_path

# Configure the game service
def configure_service(game_path):
    if not game_path:
        print("Error: Game directory not set. Please run the launcher without -play first.")
        return False

    # Verify that cod.exe exists in the game path
    if not os.path.exists(os.path.join(game_path, "cod.exe")):
        print("Error: Could not find cod.exe in the specified game directory.")
        return False

    # Check if Randgrid.sys exists in the game path
    if not os.path.exists(os.path.join(game_path, "Randgrid.sys")):
        print("Error: Could not find Randgrid.sys in the specified game directory.")
        return False

    # Check if service is already running
    if is_service_running("atvi-randgrid_sr"):
        print("Service is already running, skipping configuration")
        return True

    try:
        # Create batch file with admin elevation script
        batch_content = f"""@echo off
net session >nul 2>&1
if %errorlevel% neq 0 (
powershell -Command "Start-Process '%~f0' -Verb runAs"
exit /b
)

sc stop atvi-randgrid_sr >nul 2>&1
sc delete atvi-randgrid_sr >nul 2>&1

sc create atvi-randgrid_sr type= kernel binPath= "{game_path}\\Randgrid.sys"

sc sdset atvi-randgrid_sr D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;CCLCSWRPWPLOCRRC;;;IU)(A;;CCLCSWLOCRRC;;;SU)S:(AU;FA;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;WD)

echo Service configured successfully!
"""
        # Write the batch file to temp directory
        batch_file = os.path.join(os.environ.get('TEMP', ''), "mwii_service_config.bat")
        with open(batch_file, 'w') as f:
            f.write(batch_content)
        
        # Execute the batch file and wait for it to complete
        process = subprocess.Popen(batch_file, shell=True)
        process.wait()
        
        return True
        
    except Exception as e:
        print(f"Failed to configure service: {str(e)}")
        return False

# Launch the game
def launch_game(game_path):
    try:
        # Create a batch file to execute game
        batch_content = f"""@echo off

tasklist /FI "IMAGENAME eq bootstrapper.exe" | find /I "bootstrapper.exe" >nul
if %ERRORLEVEL%==0 (
    taskkill /F /IM bootstrapper.exe >nul
)

cd /d "{game_path}"
start "" bootstrapper.exe cod.exe hdeyguxs3zaumvlgvybm2vyc
"""
        # Write the batch file to temp directory
        temp_batch = os.path.join(os.environ.get('TEMP', ''), "mwii_launch.bat")
        with open(temp_batch, 'w') as f:
            f.write(batch_content)
        
        # Execute the batch file
        subprocess.Popen(temp_batch, shell=True)
        return True
        
    except Exception as e:
        print(f"Failed to launch game: {str(e)}")
        return False

# Custom widget that displays a background image
class BackgroundWidget(QWidget):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image = QImage(image_path)  # Load the background image
        
    # Override the paint event to draw the background image
    def paintEvent(self, event):
        if not self.image.isNull():
            painter = QPainter(self)
            # Scale the image to fit the widget while maintaining aspect ratio
            scaled_image = self.image.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Center the image in the widget
            x = (self.width() - scaled_image.width()) // 2 if scaled_image.width() > self.width() else 0
            y = (self.height() - scaled_image.height()) // 2 if scaled_image.height() > self.height() else 0
            
            # Draw the image
            painter.drawImage(x, y, scaled_image)

# Custom button with transparent background
class TransparentButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        # Make the button background transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Set the button style with CSS
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(61, 61, 61, 20);
                border: 1px solid rgba(255, 255, 255, 50);
                padding: 8px;
                border-radius: 4px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 80, 40);
                border: 1px solid rgba(255, 255, 255, 100);
            }
            QPushButton:pressed {
                background-color: rgba(40, 40, 40, 60);
            }
        """)

# Custom button with transparent background and icon
class IconButton(QPushButton):
    def __init__(self, icon_path, size=32, parent=None):
        super().__init__(parent)
        # Make the button background transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Set the button style with CSS
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(61, 61, 61, 20);
                border: 1px solid rgba(255, 255, 255, 50);
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 80, 40);
                border: 1px solid rgba(255, 255, 255, 100);
            }
            QPushButton:pressed {
                background-color: rgba(40, 40, 40, 60);
            }
        """)
        
        # Set icon if path exists
        if os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(size, size))
        else:
            print(f"Warning: Icon not found at {icon_path}")
            
        # Set fixed size for the button
        self.setFixedSize(size + 16, size + 16)  # Add padding

# Main application window
class IW9XLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        # Get the base directory for the application
        self.base_dir = get_base_dir()
        
        # Set paths relative to the base directory
        self.game_path = ""  # Store the path to the game directory
        self.settings_file = os.path.join(self.base_dir, "settings.json")  # File to store settings
        self.assets_dir = os.path.join(self.base_dir, "iw9x")
        
        self.load_settings()  # Load settings from file
        self.init_ui()  # Initialize the user interface

    # Set up the main user interface
    def init_ui(self):
        self.setWindowTitle("IW9X")  # Set window title
        self.setGeometry(100, 100, 800, 500)  # Set window size and position
        
        # Create background widget with the image
        bg_image_path = os.path.join(self.assets_dir, "res", "home.png")
        
        # Check if the background image exists, use a fallback if not
        if not os.path.exists(bg_image_path):
            print(f"Warning: Background image not found at {bg_image_path}")
            self.background_widget = QWidget()
            self.background_widget.setStyleSheet("background-color: #1e1e1e;")  # Dark fallback background
        else:
            self.background_widget = BackgroundWidget(bg_image_path)
            
        self.setCentralWidget(self.background_widget)
        
        # Main layout for the window
        main_layout = QVBoxLayout(self.background_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create stacked widget for switching between pages
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        main_layout.addWidget(self.stacked_widget)
        
        # Create main page (home screen)
        self.main_page = QWidget()
        self.main_page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.init_main_page()
        
        # Create settings page
        self.settings_page = QWidget()
        self.settings_page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.init_settings_page()
        
        # Create info page
        self.info_page = QWidget()
        self.info_page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.init_info_page()
        
        # Add pages to stacked widget
        self.stacked_widget.addWidget(self.main_page)
        self.stacked_widget.addWidget(self.settings_page)
        self.stacked_widget.addWidget(self.info_page)
        
        # Start with main page
        self.stacked_widget.setCurrentIndex(0)

    # Initialize the main page (home screen)
    def init_main_page(self):
        layout = QVBoxLayout(self.main_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Top bar with settings and info buttons
        top_bar = QHBoxLayout()
        top_bar.addStretch()  # Push buttons to the right
        
        # Info button
        info_icon_path = os.path.join(self.assets_dir, "res", "info.png")
        info_button = IconButton(info_icon_path)
        info_button.clicked.connect(self.open_info)
        top_bar.addWidget(info_button)
        
        # Settings button in top right corner
        settings_icon_path = os.path.join(self.assets_dir, "res", "settings.png")
        settings_button = IconButton(settings_icon_path)
        settings_button.clicked.connect(self.open_settings)
        top_bar.addWidget(settings_button)
        
        layout.addLayout(top_bar)

        # Title label
        title_label = QLabel("IW9X Launcher")
        title_label.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        title_label.setStyleSheet("color: white; margin-bottom: 20px;")
        layout.addWidget(title_label)

        # Spacer to push play button to bottom
        layout.addStretch()

        # Play button container (for centering)
        play_container = QHBoxLayout()
        play_container.addStretch()  # Center the button
        
        # Play button
        self.play_button = QPushButton("Play")
        self.play_button.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.play_button.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(68, 189, 50, 20);
                border: 1px solid rgba(100, 220, 80, 80);
                padding: 15px;
                border-radius: 6px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(78, 209, 60, 40);
                border: 1px solid rgba(120, 240, 100, 120);
            }
            QPushButton:pressed {
                background-color: rgba(58, 169, 40, 60);
            }
        """)
        self.play_button.setFixedSize(200, 60)  # Set button size
        self.play_button.clicked.connect(self.play_game)  # Connect to play_game method
        
        play_container.addWidget(self.play_button)
        play_container.addStretch()  # Center the button
        
        layout.addLayout(play_container)
     
    # Initialize the settings page
    def init_settings_page(self):
        layout = QVBoxLayout(self.settings_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Create a transparent panel for settings content
        panel = QWidget(self.settings_page)
        panel.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(15)
        
        # Top bar with back button
        top_bar = QHBoxLayout()
        
        # Back button to return to main page
        back_button = TransparentButton("← Back")
        back_button.clicked.connect(self.back_to_main)
        top_bar.addWidget(back_button)
        
        top_bar.addStretch()
        panel_layout.addLayout(top_bar)
        
        # Settings title
        title_label = QLabel("Settings")
        title_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        title_label.setStyleSheet("color: white; margin-bottom: 20px;")
        panel_layout.addWidget(title_label)
        
        # Game directory selection section
        path_label = QLabel("Game Directory:")
        path_label.setFont(QFont("Arial", 14))
        path_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        path_label.setStyleSheet("color: white;")
        panel_layout.addWidget(path_label)
        
        # Path input field with browse button
        path_input_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select game directory containing cod.exe...")
        self.path_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                background-color: rgba(45, 45, 45, 40);
                border: 1px solid rgba(255, 255, 255, 50);
                border-radius: 4px;
                color: white;
                selection-background-color: rgba(0, 151, 230, 80);
            }
        """)
        # Populate with saved path if available and not "null"
        if self.game_path and self.game_path.lower() != "null":
            self.path_input.setText(self.game_path)
        
        # Browse button to select game directory
        browse_button = TransparentButton("Select")
        browse_button.clicked.connect(self.browse_game_path)
        
        path_input_layout.addWidget(self.path_input)
        path_input_layout.addWidget(browse_button)
        panel_layout.addLayout(path_input_layout)
        
        # Add a note about selecting cod.exe
        note_label = QLabel("Note: Please select cod.exe from your game installation directory.")
        note_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        note_label.setStyleSheet("color: rgba(255, 255, 255, 150); font-style: italic;")
        panel_layout.addWidget(note_label)
        
        # Add DLL installation section
        dll_section_label = QLabel("Discord Game SDK:")
        dll_section_label.setFont(QFont("Arial", 14))
        dll_section_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        dll_section_label.setStyleSheet("color: white; margin-top: 20px;")
        panel_layout.addWidget(dll_section_label)
        
        # Install DLL button
        install_dll_button = QPushButton("Install Latest DLL File")
        install_dll_button.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        install_dll_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(88, 101, 242, 20);
                border: 1px solid rgba(114, 137, 218, 80);
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
                color: white;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: rgba(114, 137, 218, 40);
                border: 1px solid rgba(114, 137, 218, 120);
            }
            QPushButton:pressed {
                background-color: rgba(71, 82, 196, 60);
            }
        """)
        install_dll_button.clicked.connect(self.install_latest_dll)
        panel_layout.addWidget(install_dll_button)
        
        # Add a note about the DLL
        dll_note_label = QLabel("Note: This will download and install the latest Discord Game SDK DLL file.")
        dll_note_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        dll_note_label.setStyleSheet("color: rgba(255, 255, 255, 150); font-style: italic;")
        panel_layout.addWidget(dll_note_label)
        
        # Spacer to push save button to bottom
        panel_layout.addStretch()
        
        # Save button
        save_button = QPushButton("Save")
        save_button.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 151, 230, 20);
                border: 1px solid rgba(0, 170, 255, 80);
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
                color: white;
            }
            QPushButton:hover {
                background-color: rgba(0, 170, 255, 40);
                border: 1px solid rgba(0, 200, 255, 120);
            }
            QPushButton:pressed {
                background-color: rgba(0, 120, 200, 60);
            }
        """)
        save_button.clicked.connect(self.save_settings)
        panel_layout.addWidget(save_button)
        
        # Add panel to main layout
        layout.addWidget(panel)

    # Initialize the info page
    def init_info_page(self):
        layout = QVBoxLayout(self.info_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Create a transparent panel for info content
        panel = QWidget(self.info_page)
        panel.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(15)
        
        # Top bar with back button
        top_bar = QHBoxLayout()
        
        # Back button to return to main page
        back_button = TransparentButton("← Back")
        back_button.clicked.connect(self.back_to_main)
        top_bar.addWidget(back_button)
        
        top_bar.addStretch()
        panel_layout.addLayout(top_bar)
        
        # Info title
        title_label = QLabel("About IW9X")
        title_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        title_label.setStyleSheet("color: white; margin-bottom: 20px;")
        panel_layout.addWidget(title_label)
        
        # Info content
        info_text = QTextBrowser()
        info_text.setOpenExternalLinks(True)
        info_text.setStyleSheet("""
            QTextBrowser {
                background-color: rgba(30, 30, 30, 40);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 4px;
                color: white;
                selection-background-color: rgba(0, 151, 230, 80);
            }
        """)
        
        info_content = """
        <h2 style="color: white; text-align: center;">IW9X Launcher</h2>
        <p style="color: white;">A custom launcher for Modern Warfare II that simplifies the game startup process.</p>
        
        <h3 style="color: white;">Features:</h3>
        <ul style="color: white;">
            <li>Automatic service configuration</li>
            <li>Easy game launching</li>
            <li>Settings management</li>
            <li>Command-line support with -play option</li>
        </ul>
        
        <p style="color: white;">For support or more information, visit the project repository on <a href="https://github.com/mot204t/iw9x">GitHub</a>.</p>

        <p style="color: white;">Developed by mot204t</p>


        <center><p style="color: white;">Version 1.2.0</p></center>
        """
        
        info_text.setHtml(info_content)
        panel_layout.addWidget(info_text)
        
        # Add panel to main layout
        layout.addWidget(panel)

    # Load settings from the settings file
    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.game_path = settings.get('game_path', '')
        except Exception as e:
            print(f"Error loading settings: {e}")

    # Save settings to the settings file
    def save_settings_to_file(self):
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            
            settings = {
                'game_path': self.game_path
            }
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to save settings: {str(e)}")

    # Switch to settings page
    def open_settings(self):
        # Update path input with current path if it exists and is not "null"
        if self.game_path and self.game_path.lower() != "null":
            self.path_input.setText(self.game_path)
        else:
            self.path_input.clear()  # Clear the field if path is empty or "null"
        self.stacked_widget.setCurrentIndex(1)  # Show settings page
    
    # Return to main page
    def back_to_main(self):
        self.stacked_widget.setCurrentIndex(0)  # Show main page
    
    # Open file dialog to browse for game directory
    def browse_game_path(self):
        # Open file dialog to select cod.exe specifically
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select cod.exe",
            "",
            "Executable Files (cod.exe);;All Files (*)"
        )
        
        if file_path:
            # Check if the selected file is actually cod.exe
            if os.path.basename(file_path).lower() == "cod.exe":
                # Set the game path to the directory containing cod.exe
                game_dir = os.path.dirname(file_path)
                self.path_input.setText(game_dir)
            else:
                QMessageBox.warning(self, "Warning", "Please select cod.exe from your game directory.")
    
    # Save settings and return to main page
    def save_settings(self):
        self.game_path = self.path_input.text()
        self.save_settings_to_file()
        self.back_to_main()

    # Configure the game service
    def configure_service(self):
        if not self.game_path or self.game_path.lower() == "null":
            QMessageBox.warning(self, "Warning", "Please set the game directory in Settings first.")
            return False

        # Verify that cod.exe exists in the game path
        if not os.path.exists(os.path.join(self.game_path, "cod.exe")):
            QMessageBox.warning(self, "Warning", "Could not find cod.exe in the specified game directory. Please check your settings.")
            return False

        # Check if Randgrid.sys exists in the game path
        if not os.path.exists(os.path.join(self.game_path, "Randgrid.sys")):
            QMessageBox.warning(self, "Warning", "Could not find Randgrid.sys in the specified game directory. Please check your settings.")
            return False

        # Check if service is already running
        if is_service_running("atvi-randgrid_sr"):
            print("Service is already running, skipping configuration")
            return True

        try:
            # Create batch file with admin elevation script
            batch_content = f"""@echo off
net session >nul 2>&1
if %errorlevel% neq 0 (
powershell -Command "Start-Process '%~f0' -Verb runAs"
exit /b
)

sc stop atvi-randgrid_sr >nul 2>&1
sc delete atvi-randgrid_sr >nul 2>&1

sc create atvi-randgrid_sr type= kernel binPath= "{self.game_path}\\Randgrid.sys"

sc sdset atvi-randgrid_sr D:(A;;CCLCSWRPWPDTLOCRRC;;;SY)(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;BA)(A;;CCLCSWRPWPLOCRRC;;;IU)(A;;CCLCSWLOCRRC;;;SU)S:(AU;FA;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;WD)

echo Service configured successfully!
"""
            # Write the batch file to temp directory
            batch_file = os.path.join(os.environ.get('TEMP', ''), "mwii_service_config.bat")
            with open(batch_file, 'w') as f:
                f.write(batch_content)
            
            # Execute the batch file and wait for it to complete
            process = subprocess.Popen(batch_file, shell=True)
            process.wait()
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to configure service: {str(e)}")
            return False

    # Main play function - configures service then launches game
    def play_game(self):
        if not self.game_path or self.game_path.lower() == "null":
            QMessageBox.warning(self, "Warning", "Please set the game directory in Settings first.")
            self.open_settings()  # Open settings page directly
            return

        # Verify that cod.exe exists in the game path
        if not os.path.exists(os.path.join(self.game_path, "cod.exe")):
            QMessageBox.warning(self, "Warning", "Could not find cod.exe in the specified game directory. Please check your settings.")
            self.open_settings()  # Open settings page directly
            return

        # Configure service first
        if not self.configure_service():
            return

        # Then launch the game
        self.launch_game()

    # Launch the game
    def launch_game(self):
        try:
            # Create a batch file to execute game
            batch_content = f"""@echo off

tasklist /FI "IMAGENAME eq bootstrapper.exe" | find /I "bootstrapper.exe" >nul
if %ERRORLEVEL%==0 (
    taskkill /F /IM bootstrapper.exe >nul
)

cd /d "{self.game_path}"
start "" bootstrapper.exe cod.exe hdeyguxs3zaumvlgvybm2vyc
"""
            # Write the batch file to temp directory
            temp_batch = os.path.join(os.environ.get('TEMP', ''), "mwii_launch.bat")
            with open(temp_batch, "w") as f:
                f.write(batch_content)
            
            # Execute the batch file
            subprocess.Popen(temp_batch, shell=True)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch game: {str(e)}")

    # Switch to info page
    def open_info(self):
        self.stacked_widget.setCurrentIndex(2)  # Show info page

    # Download and install the latest DLL file
    def install_latest_dll(self):
        if not self.game_path or self.game_path.lower() == "null":
            QMessageBox.warning(self, "Warning", "Please set the game directory first.")
            return
            
        try:
            # Create the DLL directory if it doesn't exist
            dll_dir = os.path.join(self.base_dir, "iw9x", "dll")
            os.makedirs(dll_dir, exist_ok=True)
            
            # Path for the downloaded DLL
            downloaded_dll = os.path.join(dll_dir, "discord_game_sdk.dll")
            
            # Path for the game DLL
            game_dll = os.path.join(self.game_path, "discord_game_sdk.dll")
            
            # Check if the DLL already exists in the game directory
            if os.path.exists(game_dll):
                # Find the next available backup number
                backup_base = os.path.join(dll_dir, "discord_game_sdk.dll.old")
                backup_dll = backup_base
                backup_num = 1
                
                # Check if the basic backup file exists
                if os.path.exists(backup_base):
                    # Find the next available numbered backup
                    while True:
                        backup_num += 1
                        numbered_backup = f"{backup_base}{backup_num}"
                        if not os.path.exists(numbered_backup):
                            backup_dll = numbered_backup
                            break
                
                # Backup the existing DLL
                try:
                    shutil.copy2(game_dll, backup_dll)
                    print(f"Backed up existing DLL to {backup_dll}")
                except Exception as e:
                    print(f"Failed to backup existing DLL: {e}")
            
            # Check if we already have the DLL downloaded
            if os.path.exists(downloaded_dll):
                # Just copy the existing downloaded DLL to the game directory
                shutil.copy2(downloaded_dll, game_dll)
                QMessageBox.information(self, "Success", "DLL file installed successfully!")
                return
                
            # Create a progress dialog
            progress = QProgressDialog("Downloading DLL file...", "Cancel", 0, 100, self)
            progress.setWindowTitle("Download Progress")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            progress.show()
            
            # Download URL
            url = "https://cdn.discordapp.com/attachments/1377677794674479247/1377679003074167034/discord_game_sdk.dll?ex=6839d70e&is=6838858e&hm=b3e53163b6a89453aa777ecf305b4ecc7fad7a5e0e913a2551e7f93f709095de&"
            
            # Create a request with browser-like headers to avoid 403 errors
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            }
            
            request = urllib.request.Request(url, headers=headers)
            
            # Download the file with browser-like headers using urlopen
            with urllib.request.urlopen(request) as response, open(downloaded_dll, 'wb') as out_file:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                block_size = 8192
                
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                        
                    downloaded += len(buffer)
                    out_file.write(buffer)
                    
                    if total_size > 0:
                        percent = min(int(downloaded * 100 / total_size), 100)
                        progress.setValue(percent)
                        QApplication.processEvents()
                        
                        if progress.wasCanceled():
                            # Close the file and delete it if canceled
                            out_file.close()
                            if os.path.exists(downloaded_dll):
                                os.remove(downloaded_dll)
                            raise Exception("Download canceled by user")
            
            # Close the progress dialog
            progress.close()
            
            # Copy the downloaded DLL to the game directory
            shutil.copy2(downloaded_dll, game_dll)
            
            QMessageBox.information(self, "Success", "DLL file downloaded and installed successfully!")
            
        except Exception as e:
            progress = QProgressDialog("", "", 0, 100, self)
            progress.close()
            QMessageBox.critical(self, "Error", f"Failed to install DLL file: {str(e)}")

# Direct play function for command line mode
def direct_play():
    # Check if running as admin, if not, restart with admin privileges
    if not is_admin():
        print("Restarting with admin privileges for direct play...")
        run_as_admin()
        sys.exit(0)
        
    # Load game path from settings
    game_path = load_settings()
    
    # Check if game path is set and not "null"
    if not game_path or game_path.lower() == "null":
        print("Error: Game directory not set. Please run the launcher without -play first.")
        sys.exit(1)
    
    # Verify that cod.exe exists in the game path
    if not os.path.exists(os.path.join(game_path, "cod.exe")):
        print("Error: Could not find cod.exe in the specified game directory.")
        sys.exit(1)
        
    # Configure service if needed
    if not configure_service(game_path):
        print("Failed to configure service. Exiting.")
        sys.exit(1)
    
    # Launch the game
    if not launch_game(game_path):
        print("Failed to launch game. Exiting.")
        sys.exit(1)
    
    print("Game launched successfully.")
    # Exit after launching
    sys.exit(0)

# Main entry point
def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='IW9X Launcher')
    parser.add_argument('-play', action='store_true', help='Launch the game directly without showing the GUI')
    args = parser.parse_args()
    
    # If -play argument is provided, launch the game directly
    if args.play:
        direct_play()
        return
    
    # Check if running as admin, if not, restart with admin privileges
    if not is_admin():
        print("Restarting with admin privileges...")
        run_as_admin()
        sys.exit(0)
    
    # Check and download resources if any are missing
    check_and_download_resources()
    
    # Create and run the application
    app = QApplication(sys.argv)
    
    # Set application icon
    icon_path = os.path.join(get_base_dir(), "iw9x", "res", "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    launcher = IW9XLauncher()
    launcher.show()
    sys.exit(app.exec())


# Run the application
if __name__ == "__main__":
    main() 