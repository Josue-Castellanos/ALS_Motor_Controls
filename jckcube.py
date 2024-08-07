"""
    Josue B. Castellanos 
    6/17/24 -- 8/6/24
    https://github.com/Josue-Castellanos/ALS_Motor_Controls
    (c) Lawrence Berkelay National Laboratory, 2024
    python file: jckcube.py

    **This version is only compatible with PySpin for Spinnaker 3.0.0.118 and Python 3.10**
    **If your Matlab/LabView supports newer versions of Spinnaker (like 3.2.0.62)**
    **I would recommend updating to that version, for both Spinnaker/PySpin**
"""

import time
import clr 

# Add reference to the Thorlabs Kinesis DLLs (Dynamic-Link Libraries)
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.KCube.DCServoCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.KCube.BrushlessMotorCLI.dll")

# Import the namespaces from the Thorlabs Kinesis DLLs
from Thorlabs.MotionControl.DeviceManagerCLI import *          # type: ignore
from Thorlabs.MotionControl.GenericMotorCLI import *             # type: ignore
from Thorlabs.MotionControl.GenericMotorCLI.ControlParameters import JogParametersBase # type: ignore
from Thorlabs.MotionControl.KCube.DCServoCLI import *   # type: ignore
from Thorlabs.MotionControl.KCube.BrushlessMotorCLI import *          # type: ignore
from System import Decimal # type: ignore

# Initialize the DeviceManager
DeviceManagerCLI.BuildDeviceList() # type: ignore

class MaskMotor:
    def __init__(self, serial_no_x, serial_no_y, serial_no_z, log_signal=None):
        self.serial_no_x = serial_no_x
        self.serial_no_y = serial_no_y
        self.serial_no_z = serial_no_z
        self.motor_x = None
        self.motor_y = None
        self.motor_z = None
        self.log_signal = log_signal if log_signal else print

    def log(self, level, component, message, details=""):
        self.log_signal(level, component, message, details)

    def ConnectMotor(self, serial_no):
        try:
            if serial_no == str('28252438'):
                motor = KCubeBrushlessMotor.CreateKCubeBrushlessMotor(serial_no) # type: ignore
            else:
                motor = KCubeDCServo.CreateKCubeDCServo(serial_no) # type: ignore

            # If Serial Number is assigned connect motor
            if not motor == None:
                motor.Connect(serial_no)

                # Wait for the device settings to initialize
                if not motor.IsSettingsInitialized():
                    motor.WaitForSettingsInitialized(10000)  # 10 seconds timeout
                    assert motor.IsSettingsInitialized() is True

                # Start Polling the Device
                motor.StartPolling(50)
                time.sleep(.1)

                # Enable the device
                motor.EnableDevice()
                time.sleep(.1)

                # Load and Update motor configuration

                if serial_no == str('28252438'):
                    config = motor.LoadMotorConfiguration(serial_no, DeviceConfiguration.DeviceSettingsUseOptionType.UseDeviceSettings) # type: ignore
                    config.DeviceSettingsName = str('DDS050') # Optics stage 
                else:
                    config = motor.LoadMotorConfiguration(serial_no, DeviceConfiguration.DeviceSettingsUseOptionType.UseFileSettings) # type: ignore
                    config.DeviceSettingsName = str('MTS50-Z8') # Mask Stage
                config.UpdateCurrentConfiguration()
                motor.SetSettings(motor.MotorDeviceSettings, True, False)
                self.log("INFO", "MotorControl", f"Motor {serial_no} connected", f"Stage {config.DeviceSettingsName}")

            
        except Exception as e:
            self.log("ERROR", "MotorControl", "Failed to connect motor", str(e))
        return motor

    def ConnectAllMotors(self):
        self.motor_x = self.ConnectMotor(self.serial_no_x)
        self.motor_y = self.ConnectMotor(self.serial_no_y)
        self.motor_z = self.ConnectMotor(self.serial_no_z)

    def GetPosition(self, motor):
        position = motor.Position
        return position

    def SetVelocityParams(self, motor, max_velocity, acceleration):
        vel_params = motor.GetVelocityParams()
        vel_params.MaxVelocity = max_velocity
        vel_params.Acceleration = acceleration
        motor.SetVelParams(vel_params)
        self.log("INFO", "MotorControl", "Velocity parameters set", f"Max Velocity={max_velocity} mm/s, Acceleration={acceleration} mm/s^2")

    def SetJogParams(self, motor, step_size):
        jog_params = motor.GetJogParams()
        jog_params.StepSize = Decimal(step_size)
        jog_params.JogMode = JogParametersBase.JogModes.SingleStep
        motor.SetJogParams(jog_params)
        self.log("INFO", "MotorControl", "Jog parameters set", f"Step Size={step_size} mm, Mode=SingleStep")

    def SetMotorParams(self, motor, stop_mode, backlash_distance):
        motor_params = motor.GetMotorParams()
        motor_params.StopMode = stop_mode
        motor_params.BacklashCompensation = backlash_distance
        motor.SetMotorParams(motor_params)
        self.log("INFO", "MotorControl", "Motor parameters set", f"Stop Mode={stop_mode}, Backlash Distance={backlash_distance} mm")

    def SetAllParameters(self, step_size):
        self.SetJogParams(self.motor_x, step_size)
        self.SetJogParams(self.motor_y, step_size)
        self.SetJogParams(self.motor_z, step_size)

    def MoveMotor(self, motor, position, axis_name):
        self.log("INFO", "MotorControl", "Moving motor", f"Axis={axis_name}, Position={position} mm")
        motor.MoveTo(Decimal(position), 60000)  # 60 seconds timeout in milliseconds

        # Wait for the device to complete the move
        while motor.Status.IsMoving:
            time.sleep(0.1)  # Check every 100ms
        self.log("INFO", "MotorControl", "Motor move completed", f"Axis={axis_name}")

    def MoveAllMotors(self, position_x, position_y, position_z):
        self.MoveMotor(self.motor_x, position_x, "X")
        self.MoveMotor(self.motor_y, position_y, "Y")
        self.MoveMotor(self.motor_z, position_z, "Z")

    def ForwardJogMotor(self, motor):
        self.log("INFO", "MotorControl", "Jogging motor forward", "")
        motor.MoveJog(MotorDirection.Forward, 60000) # type: ignore # Wait time in milliseconds
        # Wait for the device to complete the move
        while motor.Status.IsMoving:
            time.sleep(0.1)  # Check every 100ms
            
        self.log("INFO", "MotorControl", "Motor jog completed", "Forward")

    def BackwardJogMotor(self, motor):
        self.log("INFO", "MotorControl", "Jogging motor backward", "")
        motor.MoveJog(MotorDirection.Backward, 60000) # type: ignore # Wait time in milliseconds
        self.log("INFO", "MotorControl", "Motor jog completed", "Backward")

    def DisconnectMotor(self, motor):
        motor.StopPolling()
        motor.Disconnect(False)
        self.log("INFO", "MotorControl", f"Disconnected Motor {motor}")

    def DisconnectAllMotors(self):
        self.DisconnectMotor(self.motor_x)
        self.DisconnectMotor(self.motor_y)
        self.DisconnectMotor(self.motor_z)

