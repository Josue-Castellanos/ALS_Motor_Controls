import sys
import json
import PySpin
import threading
from jckcube import MaskMotor
from jcflir import Camera
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QHBoxLayout, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QFormLayout, QGridLayout, QProgressBar
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from datetime import datetime

SETTINGS_FILE = "settings.txt"

class CameraGUI(QMainWindow):
    # Define a signal for progress updates
    progress_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.serial_no_x = str('27263196')
        self.serial_no_y = str('27263127') 
        self.serial_no_z = str('28252438')

        self.setWindowTitle("PX LDRD Motion Control")
        self.setGeometry(100, 100, 1700, 1000)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        # Load settings from file
        self.settings = self.LoadSettings()

        # Left control panel
        self.control_panel = QWidget()
        self.control_panel.setFixedWidth(300)  # Set a fixed width for the control panel
        self.main_layout.addWidget(self.control_panel)
        self.InitControlPanel()

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

        # Info bar below the image, I still need to implement the cursor logic for this feature
        self.info_bar = QLabel("Cursor Position: X:0, Y:0 | Zoom Level: 100% | FPS: 0")
        self.right_layout.addWidget(self.info_bar)

        self.log_table = QTableWidget(0, 5)  # 0 rows initially, 5 columns
        self.log_table.setHorizontalHeaderLabels(["Timestamp", "Logger", "Component", "Message", "Details"])
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.right_layout.addWidget(self.log_table)

        # Default motor
        self.mask_motor = MaskMotor(self.serial_no_x, self.serial_no_y, self.serial_no_z, log_signal=self.log_message)
        self.InitCameraSettings()

        # Connect the progress signal to the slot method
        self.progress_signal.connect(self.UpdateProgressBar)


    def InitControlPanel(self):
        control_layout = QVBoxLayout()
        
        # Add Start and Stop Buttons
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)  # Disable Stop button initially
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)

        # Mask Section (X and Y motors)
        mask_group = QGroupBox("Mask Control (X and Y)")
        mask_layout = QVBoxLayout()

        # X and Y jog controls
        jog_layout = QGridLayout()
        
        # X axis controls
        self.jog_x_backward_btn = QPushButton("◀ X") 
        self.jog_x_forward_btn = QPushButton("X ▶")
        jog_layout.addWidget(self.jog_x_backward_btn, 1, 0)
        jog_layout.addWidget(self.jog_x_forward_btn, 1, 2)
        
        # Y axis controls
        self.jog_y_backward_btn = QPushButton("▲ Y")
        self.jog_y_forward_btn = QPushButton("▼ Y")
        jog_layout.addWidget(self.jog_y_backward_btn, 0, 1)
        jog_layout.addWidget(self.jog_y_forward_btn, 2, 1)
        
        mask_layout.addLayout(jog_layout)

        # X and Y absolute move controls
        abs_layout = QHBoxLayout()
        
        x_abs_layout = QHBoxLayout()
        x_abs_layout.addWidget(QLabel("X:"))
        self.x_position_input = QLineEdit()
        x_abs_layout.addWidget(self.x_position_input)
        self.x_move_btn = QPushButton("Move X")
        x_abs_layout.addWidget(self.x_move_btn)
        
        y_abs_layout = QHBoxLayout()
        y_abs_layout.addWidget(QLabel("Y:"))
        self.y_position_input = QLineEdit()
        y_abs_layout.addWidget(self.y_position_input)
        self.y_move_btn = QPushButton("Move Y")
        y_abs_layout.addWidget(self.y_move_btn)
        
        abs_layout.addLayout(x_abs_layout)
        abs_layout.addLayout(y_abs_layout)
        
        mask_layout.addLayout(abs_layout)

        # Step Size Control for X and Y
        xy_step_size_layout = QHBoxLayout()
        xy_step_size_layout.addWidget(QLabel("XY Step Size (mm):"))
        self.xy_step_size_input = QLineEdit()
        xy_step_size_layout.addWidget(self.xy_step_size_input)
        self.save_xy_step_size_btn = QPushButton("Save XY")
        xy_step_size_layout.addWidget(self.save_xy_step_size_btn)
        mask_layout.addLayout(xy_step_size_layout)

        mask_group.setLayout(mask_layout)
        control_layout.addWidget(mask_group)

        # Mirror Section (Z motor)
        mirror_group = QGroupBox("Mirror Control (Z)")
        mirror_layout = QVBoxLayout()

        # Z jog controls
        z_jog_layout = QHBoxLayout()
        self.jog_z_backward_btn = QPushButton("◀ Z")
        self.jog_z_forward_btn = QPushButton("Z ▶")
        z_jog_layout.addWidget(self.jog_z_backward_btn)
        z_jog_layout.addWidget(self.jog_z_forward_btn)
        mirror_layout.addLayout(z_jog_layout)

        # Z absolute move control
        z_abs_layout = QHBoxLayout()
        z_abs_layout.addWidget(QLabel("Z:"))
        self.z_position_input = QLineEdit()
        z_abs_layout.addWidget(self.z_position_input)
        self.z_move_btn = QPushButton("Move Z")
        z_abs_layout.addWidget(self.z_move_btn)
        mirror_layout.addLayout(z_abs_layout)

        # Step Size Control for Z
        z_step_size_layout = QHBoxLayout()
        z_step_size_layout.addWidget(QLabel("Z Step Size (mm):"))
        self.z_step_size_input = QLineEdit()
        z_step_size_layout.addWidget(self.z_step_size_input)
        self.save_z_step_size_btn = QPushButton("Save Z")
        z_step_size_layout.addWidget(self.save_z_step_size_btn)
        mirror_layout.addLayout(z_step_size_layout)

        mirror_group.setLayout(mirror_layout)
        control_layout.addWidget(mirror_group)

        # Scan Control Section
        scan_group = QGroupBox("Scan Control")
        scan_layout = QVBoxLayout()

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

        scan_step_size_layout = QHBoxLayout()
        scan_step_size_layout.addWidget(QLabel("Scan Step Size (mm):"))
        self.scan_step_size_input = QLineEdit()
        scan_step_size_layout.addWidget(self.scan_step_size_input)
        scan_layout.addLayout(scan_step_size_layout)

        self.scan_btn = QPushButton("Start Scan")
        scan_layout.addWidget(self.scan_btn)

        # Add a progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        scan_layout.addWidget(self.progress_bar)        

        scan_group.setLayout(scan_layout)
        control_layout.addWidget(scan_group)

        # Set the control panel layout
        self.control_panel.setLayout(control_layout)

        # Connect button signals
        self.jog_x_backward_btn.clicked.connect(lambda: self.JogMotor("X", "backward"))
        self.jog_x_forward_btn.clicked.connect(lambda: self.JogMotor("X", "forward"))
        self.jog_y_backward_btn.clicked.connect(lambda: self.JogMotor("Y", "backward"))
        self.jog_y_forward_btn.clicked.connect(lambda: self.JogMotor("Y", "forward"))
        self.jog_z_backward_btn.clicked.connect(lambda: self.JogMotor("Z", "backward"))
        self.jog_z_forward_btn.clicked.connect(lambda: self.JogMotor("Z", "forward"))
        
        self.x_move_btn.clicked.connect(lambda: self.StartMove("X"))
        self.y_move_btn.clicked.connect(lambda: self.StartMove("Y"))
        self.z_move_btn.clicked.connect(lambda: self.StartMove("Z"))
        
        self.save_xy_step_size_btn.clicked.connect(lambda: self.SaveStepSize("XY"))
        self.save_z_step_size_btn.clicked.connect(lambda: self.SaveStepSize("Z"))
        
        self.scan_btn.clicked.connect(self.StartScan)
        self.start_btn.clicked.connect(self.StartHardware)
        self.stop_btn.clicked.connect(self.StopHardware)



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


    def InitCameraSettings(self):
        # Camera Settings
        settings_group = QGroupBox("Camera Settings")
        settings_layout = QFormLayout()
        settings_group.setLayout(settings_layout)
        
        # Gain setting
        self.gain_input = QLineEdit(str(self.settings['gain']))
        settings_layout.addRow("Gain:", self.gain_input)

        # Exposure time setting
        self.exposure_input = QLineEdit(str(self.settings['exposure_time']))
        settings_layout.addRow("Exposure Time (μs):", self.exposure_input)

        # Apply settings button
        self.apply_settings_btn = QPushButton("Apply Settings")
        self.apply_settings_btn.clicked.connect(self.ApplySettings)
        settings_layout.addRow(self.apply_settings_btn)

        # Add the settings group to the bottom of the control panel
        self.control_panel.layout().addWidget(settings_group)


    def LoadSettings(self):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'exposure_time': 1400,
                'gain': 0
            }
        

    def SaveSettings(self):
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(self.settings, f)
        

    def SaveStepSize(self, axis):
        if axis == "XY":
            step_size = float(self.xy_step_size_input.text())
            self.mask_motor.SetJogParams(self.mask_motor.motor_x, step_size)
            self.mask_motor.SetJogParams(self.mask_motor.motor_y, step_size)
            self.log_message("INFO", "MotorControl", "XY Jog step size updated", f"New step size: {step_size} mm")
        elif axis == "Z":
            step_size = float(self.z_step_size_input.text())
            self.mask_motor.SetJogParams(self.mask_motor.motor_z, step_size)
            self.log_message("INFO", "MotorControl", "Z Jog step size updated", f"New step size: {step_size} mm")


    def JogMotor(self, axis, direction):
        motor = getattr(self.mask_motor, f"motor_{axis.lower()}")
        if direction == "forward":
            self.mask_motor.ForwardJogMotor(motor)
            self.log_message("INFO", "MotorControl", f"{axis} motor jogged forward", "Forward")
        elif direction == 'backward':
            self.mask_motor.BackwardJogMotor(motor)
            self.log_message("INFO", "MotorControl", f"{axis} motor jogged backward", "Backward")


    def StartMove(self, axis):
        try:
            motor = getattr(self.mask_motor, f"motor_{axis.lower()}")

            # Start move in a separate thread
            move_thread = threading.Thread(target=self.MoveThread, args=(axis, motor))
            move_thread.start()

        except ValueError:
            self.log_message("ERROR", "MotorControl", "Invalid input", "Please enter valid numbers for start position, target position, and step size")
        except Exception as e:
            self.log_message("ERROR", "MotorControl", "Move failed", str(e))


    def MoveThread(self, axis, motor):
        try:
            position_input = getattr(self, f"{axis.lower()}_position_input")
            position = float(position_input.text())
            self.mask_motor.MoveMotor(motor, position, axis)
            self.log_message("INFO", "MotorControl", f"{axis} motor moved to absolute position", f"Position: {position} mm")

        except ValueError:
            self.log_message("ERROR", "MotorControl", "Invalid input", "Please enter valid number", "Range: 0 - 50")
        except Exception as e:
            self.log_message("ERROR", "MotorControl", "Move failed", str(e))


    def StartScan(self):
        try:
            start_position = float(self.start_position_input.text())
            target_position = float(self.target_position_input.text())
            step_size = float(self.scan_step_size_input.text())

            # Start scan in a separate thread
            scan_thread = threading.Thread(target=self.ScanThread, args=(start_position, target_position, step_size))
            scan_thread.start()

        except ValueError:
            self.log_message("ERROR", "ScanMode", "Invalid input", "Please enter valid numbers for start position, target position, and step size")
        except Exception as e:
            self.log_message("ERROR", "ScanMode", "Scan failed", str(e))


    def ScanThread(self, start_position, target_position, step_size):
        try: 
            current_motor = self.mask_motor.motor_z
            axis = "Z"

            # Save step size
            self.mask_motor.SetJogParams(current_motor, step_size)
            self.log_message("INFO", "ScanMode", f"Jog step size set for {axis} scan", f"Step size: {step_size} mm")

            self.mask_motor.MoveMotor(current_motor, start_position, axis)

            # Calculate the number of steps
            num_steps = int(abs(target_position - start_position) / step_size)

            # Determine the direction of scan
            direction = "forward" if target_position > start_position else "backward"

            for step in range(num_steps + 1):
                if step == 0:
                    self.camera.AcquireImage(step + 1)
                    current_position = self.mask_motor.GetPosition(current_motor)
                    self.log_message("INFO", "ScanMode", "Image acquired", f"Position: {current_position} mm")
                else:
                    if direction == "forward":
                        self.mask_motor.ForwardJogMotor(current_motor)
                    else:
                        self.mask_motor.BackwardJogMotor(current_motor)

                    current_position = self.mask_motor.GetPosition(current_motor)
                    #self.log_message("INFO", "ScanMode", "Motor jogged to position", f"Position: {current_position} mm")

                    # Acquire image
                    """
                        ================================
                        We can apply our save logic here
                        ================================
                    """
                    self.camera.AcquireImage(step + 1)
                    self.log_message("INFO", "ScanMode", "Image acquired", f"Position: {current_position} mm")
                            # Update progress
                progress_value = int((step / num_steps) * 100)
                self.progress_signal.emit(progress_value)

            # Reset progress bar
            self.log_message("INFO", "ScanMode", "Scan complete", "")
            self.progress_signal.emit(0)
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


    def UpdateProgressBar(self, value):
        self.progress_bar.setValue(value)


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

    def DeinitHardware(self):
        self.timer.stop()
        self.position_timer.stop()

        if hasattr(self, 'camera'):
            self.camera.DisconnectCamera()

        if hasattr(self, 'mask_motor'):
            self.mask_motor.DisconnectAllMotors()

        self.log_message("INFO", "Deinitialize", "Disconnected camera and motors", "Waiting to Initialize Hardware")

    def StartHardware(self):
        self.InitHardware()  # Initialize hardware
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)


    def StopHardware(self):
        self.DeinitHardware()  # This will trigger closeEvent
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)


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
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
