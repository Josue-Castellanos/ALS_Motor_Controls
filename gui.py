import sys
import time
import json
import PySpin
from jckcube import MaskMotor
from jcflir import Camera
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QComboBox, QHBoxLayout, QLineEdit, QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QFormLayout
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt
from datetime import datetime

SETTINGS_FILE = "settings.txt"

class CameraGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.serial_no_x = str('27263196')
        self.serial_no_y = str('27263127') 
        self.serial_no_z = str('28252438')

        self.setWindowTitle("Camera Control")
        self.setGeometry(100, 100, 1700, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        # Load settings from file
        self.settings = self.LoadSettings()

        # Left control panel
        self.control_panel = QWidget()
        self.control_panel.setFixedWidth(300)  # Set a fixed width for the control panel
        self.control_layout = QVBoxLayout(self.control_panel)
        self.main_layout.addWidget(self.control_panel)

        # Motor selection
        self.motor_combo = QComboBox()
        self.motor_combo.addItems(["X", "Y", "Z"])
        self.motor_combo.currentIndexChanged.connect(self.ChangeMotor)
        self.control_layout.addWidget(QLabel("Select Motor:"))
        self.control_layout.addWidget(self.motor_combo)

        # Mode selection
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Jog Mode", "Absolute Move", "Scan Mode"])
        self.mode_combo.currentIndexChanged.connect(self.ChangeMode)
        self.control_layout.addWidget(self.mode_combo)

        self.mode_stack = QStackedWidget()
        self.control_layout.addWidget(self.mode_stack)

        # Initialize mode-specific widgets
        self.InitJogMode()
        self.InitAbsoluteMode()
        self.InitScanMode()
        self.InitCameraSettings()

        # Right side: Camera stream and info
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.main_layout.addWidget(self.right_panel, 1)  # This widget should expand

        # Position labels
        self.position_labels_layout = QHBoxLayout()
        self.position_label_x = QLabel("X: 0.0 mm")
        self.position_label_y = QLabel("Y: 0.0 mm")
        self.position_label_z = QLabel("Z: 0.0 mm")
        self.position_labels_layout.addWidget(self.position_label_x)
        self.position_labels_layout.addWidget(self.position_label_y)
        self.position_labels_layout.addWidget(self.position_label_z)
        self.right_layout.addLayout(self.position_labels_layout)

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.right_layout.addWidget(self.image_label, 1)  # Make the image expandable

        # Info bar below the image
        self.info_bar = QLabel("Cursor Position: X:0, Y:0 | Zoom Level: 100% | FPS: 0")
        self.right_layout.addWidget(self.info_bar)

        self.log_table = QTableWidget(0, 5)  # 0 rows initially, 5 columns
        self.log_table.setHorizontalHeaderLabels(["Timestamp", "Logger", "Component", "Message", "Details"])
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.right_layout.addWidget(self.log_table)

        # Default motor
        self.mask_motor = MaskMotor(self.serial_no_x, self.serial_no_y, self.serial_no_z, log_signal=self.log_message)
        self.motor_combo.setCurrentText("Z")

    def InitJogMode(self):
        jog_widget = QWidget()
        jog_layout = QVBoxLayout(jog_widget)

        step_size_layout = QHBoxLayout()
        step_size_layout.addWidget(QLabel("Step Size (mm):"))
        self.step_size_input = QLineEdit()
        step_size_layout.addWidget(self.step_size_input)
        self.SaveStepSize_btn = QPushButton("Save")
        self.SaveStepSize_btn.clicked.connect(self.SaveStepSize)
        step_size_layout.addWidget(self.SaveStepSize_btn)
        jog_layout.addLayout(step_size_layout)

        jog_buttons_layout = QHBoxLayout()
        self.jog_backward_btn = QPushButton("◀ Backward")
        self.jog_backward_btn.clicked.connect(lambda: self.JogMotor("backward"))
        jog_buttons_layout.addWidget(self.jog_backward_btn)
        self.jog_forward_btn = QPushButton("Forward ▶")
        self.jog_forward_btn.clicked.connect(lambda: self.JogMotor("forward"))
        jog_buttons_layout.addWidget(self.jog_forward_btn)
        jog_layout.addLayout(jog_buttons_layout)

        self.mode_stack.addWidget(jog_widget)

    def InitAbsoluteMode(self):
        abs_widget = QWidget()
        abs_layout = QVBoxLayout(abs_widget)

        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("Position (mm):"))
        self.position_input = QLineEdit()
        position_layout.addWidget(self.position_input)
        self.MoveTo_btn = QPushButton("Move")
        self.MoveTo_btn.clicked.connect(self.MoveTo)
        position_layout.addWidget(self.MoveTo_btn)
        abs_layout.addLayout(position_layout)

        self.mode_stack.addWidget(abs_widget)

    def InitScanMode(self):
        scan_widget = QWidget()
        scan_layout = QVBoxLayout(scan_widget)

        start_position_layout = QHBoxLayout()
        start_position_layout.addWidget(QLabel("Start Position (mm):"))
        self.start_position_input = QLineEdit()
        start_position_layout.addWidget(self.start_position_input)
        scan_layout.addLayout(start_position_layout)

        target_position_layout = QHBoxLayout()
        target_position_layout.addWidget(QLabel("Target Position (mm):"))
        self.target_position_input = QLineEdit()
        target_position_layout.addWidget(self.target_position_input)
        scan_layout.addLayout(target_position_layout)

        step_size_layout = QHBoxLayout()
        step_size_layout.addWidget(QLabel("Step Size (mm):"))
        self.scan_step_size_input = QLineEdit()
        step_size_layout.addWidget(self.scan_step_size_input)
        scan_layout.addLayout(step_size_layout)

        self.scan_btn = QPushButton("Start Scan")
        self.scan_btn.clicked.connect(self.StartScan)
        scan_layout.addWidget(self.scan_btn)

        self.mode_stack.addWidget(scan_widget)

    def InitCameraSettings(self):
        # Camera Settings
        self.settings_group = QGroupBox("Camera Settings")
        self.settings_layout = QFormLayout()
        self.settings_group.setLayout(self.settings_layout)
        
        # Gain setting
        self.gain_input = QLineEdit(str(self.settings['gain']))
        self.settings_layout.addRow("Gain:", self.gain_input)

        # Exposure time setting
        self.exposure_input = QLineEdit(str(self.settings['exposure_time']))
        self.settings_layout.addRow("Exposure Time (μs):", self.exposure_input)

        # Apply settings button
        self.apply_settings_btn = QPushButton("Apply Settings")
        self.apply_settings_btn.clicked.connect(self.ApplySettings)
        self.settings_layout.addRow(self.apply_settings_btn)

        # Add the settings group to the bottom of the control panel
        self.control_layout.addStretch()
        self.control_layout.addWidget(self.settings_group)

    def LoadSettings(self):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'exposure_time': 0.0003,
                'gain': 0
            }
        
    def SaveSettings(self):
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(self.settings, f)
        
    def ChangeMode(self, index):
        self.mode_stack.setCurrentIndex(index)

    def ChangeMotor(self):
        motor_selection = self.motor_combo.currentText()
        if motor_selection == "X":
            self.current_motor = self.mask_motor.motor_x
        elif motor_selection == "Y":
            self.current_motor = self.mask_motor.motor_y
        else:
            self.current_motor = self.mask_motor.motor_z
        self.log_message("INFO", "MotorControl", "Motor selection changed", f"Selected Motor: {motor_selection}")


    def SaveStepSize(self):
        step_size = float(self.step_size_input.text())
        self.mask_motor.SetJogParams(self.current_motor, step_size)
        self.log_message("INFO", "MotorControl", "Jog step size updated", f"New step size: {step_size} mm")

    def JogMotor(self, direction):
        if direction == "forward":
            self.mask_motor.ForwardJogMotor(self.current_motor)
            self.log_message("INFO", "MotorControl", "Motor jogged forward", f"Axis: {self.motor_combo.currentText()}")
        elif direction == 'backward':
            self.mask_motor.BackwardJogMotor(self.current_motor)
            self.log_message("INFO", "MotorControl", "Motor jogged backward", f"Axis: {self.motor_combo.currentText()}")

    def MoveTo(self):
        position = float(self.position_input.text())
        self.mask_motor.MoveMotor(self.current_motor, position, self.motor_combo.currentText())
        self.log_message("INFO", "MotorControl", "Motor moved to absolute position", f"Axis: {self.motor_combo.currentText()}, Position: {position} mm")

    def StartScan(self):
        try:
            start_position = float(self.start_position_input.text())
            target_position = float(self.target_position_input.text())
            step_size = float(self.scan_step_size_input.text())

            # Save step size
            self.mask_motor.SetJogParams(self.current_motor, step_size)
            self.log_message("INFO", "ScanMode", "Jog step size set for scan", f"Step size: {step_size} mm")

            self.mask_motor.MoveMotor(self.current_motor, start_position, self.motor_combo.currentText())

            # Calculate the number of steps
            num_steps = int(abs(target_position - start_position) / step_size)

            # Determine the direction of scan
            direction = "forward" if target_position > start_position else "backward"

            for step in range(num_steps + 1):
                current_position = start_position + step * step_size * (1 if direction == "forward" else -1)
                
                if direction == "forward":
                    self.mask_motor.ForwardJogMotor(self.current_motor)
                else:
                    self.mask_motor.BackwardJogMotor(self.current_motor)

                self.log_message("INFO", "ScanMode", "Motor jogged to position", f"Position: {current_position} mm")

                # Acquire image
                """
                    ================================
                    We can apply our save logic here
                    ================================
                """
                self.camera.AcquireImage(step + 1)
                self.log_message("INFO", "ScanMode", "Image acquired", f"Position: {current_position} mm")

            self.log_message("INFO", "ScanMode", "Scan complete", "")
        except ValueError:
            self.log_message("ERROR", "ScanMode", "Invalid input", "Please enter valid numbers for start position, target position, and step size")
        except Exception as e:
            self.log_message("ERROR", "ScanMode", "Scan failed", str(e))

    def log_message(self, level, component, message, details=""):
        logger = level
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        row_position = self.log_table.rowCount()
        self.log_table.insertRow(row_position)
        self.log_table.setItem(row_position, 0, QTableWidgetItem(timestamp))
        self.log_table.setItem(row_position, 1, QTableWidgetItem(logger))
        self.log_table.setItem(row_position, 2, QTableWidgetItem(component))
        self.log_table.setItem(row_position, 3, QTableWidgetItem(message))
        self.log_table.setItem(row_position, 4, QTableWidgetItem(details))
        self.log_table.scrollToBottom()

    def UpdateFrame(self):
        try:
            if hasattr(self, 'camera') and hasattr(self.camera, 'cam'):
                frame, width, height = self.camera.GetFrame()
                if frame is not None:
                    bytes_per_line = 3 * width
                    q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(q_image)
                    self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except PySpin.SpinnakerException as ex:
            self.log_message("ERROR", "CameraCapture", "Frame acquisition failed", str(ex))
        except AttributeError:
            # Camera is already disconnected, stop the timer
            self.timer.stop()

    def UpdatePositions(self):
        try:
            position_x = self.mask_motor.GetPosition(self.mask_motor.motor_x)
            position_y = self.mask_motor.GetPosition(self.mask_motor.motor_y)
            position_z = self.mask_motor.GetPosition(self.mask_motor.motor_z)
            self.position_label_x.setText(f"X: {position_x} mm")
            self.position_label_y.setText(f"Y: {position_y} mm")
            self.position_label_z.setText(f"Z: {position_z} mm")
        except Exception as e:
            self.log_message("ERROR", "PositionUpdate", "Failed to update positions", str(e))

    def ApplySettings(self):
        try:
            gain_value = float(self.gain_input.text())
            exposure_time = float(self.exposure_input.text())
            
            if self.camera.SetCameraSettings(gain_value, exposure_time):
                self.settings['gain'] = gain_value
                self.settings['exposure_time'] = exposure_time
                
                self.SaveSettings()
                
                self.log_message("INFO", "CameraSettings", "Settings applied and saved successfully")
            else:
                self.log_message("ERROR", "CameraSettings", "Failed to apply settings")
        except ValueError:
            self.log_message("ERROR", "CameraSettings", "Invalid input", "Please enter valid numbers for gain and exposure time")

    def InitHardware(self):
        try:
            self.camera = Camera(log_signal=self.log_message)
            self.camera.ConnectCamera()
            self.log_message("INFO", "Initialization", "Camera connected", "")

            self.mask_motor.ConnectAllMotors()
            self.log_message("INFO", "Initialization", "Motors connected", f"Serial numbers: X={self.serial_no_x}, Y={self.serial_no_y}, Z={self.serial_no_z}")

            # Start the timers after initialization
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.UpdateFrame)
            self.timer.start(33)  # Update every ~33 ms (30 fps)

            self.position_timer = QTimer(self)
            self.position_timer.timeout.connect(self.UpdatePositions)
            self.position_timer.start(500)  # Update positions every second
        except Exception as e:
            self.log_message("ERROR", "Initialization", "Failed to initialize hardware", str(e))
            
    def closeEvent(self, event):
        self.timer.stop()
        self.position_timer.stop()

        if hasattr(self, 'camera'):
            self.camera.DisconnectCamera()

        if hasattr(self, 'mask_motor'):
            self.mask_motor.DisconnectAllMotors()

        self.log_message("INFO", "Shutdown", "Application closing", "Disconnecting camera and motors")
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    window = CameraGUI()
    window.show()
    time.sleep(3)
    QTimer.singleShot(0, window.InitHardware)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
