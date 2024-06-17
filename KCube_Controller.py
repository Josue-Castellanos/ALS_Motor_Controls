import time
import clr 

# Add reference to the Thorlabs Kinesis DLLs (Dynaimic-Link Libraries)
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.KCube.DCServoCLI.dll")

# Import the namespaces from the Thorlabs Kinesis DLLs
from Thorlabs.MotionControl.DeviceManagerCLI import *         
from Thorlabs.MotionControl.GenericMotorCLI import *            
from Thorlabs.MotionControl.GenericMotorCLI import KCubeMotor
from Thorlabs.MotionControl.GenericMotorCLI.ControlParameters import JogParametersBase
from Thorlabs.MotionControl.KCube.DCServoCLI import *           
from System import Decimal

# Initialize the DeviceManager
DeviceManagerCLI.BuildDeviceList()

# 
class MaskMotor:
    def __init__(self, serial_no_z, serial_no_x, serial_no_y):
        self.serial_no_z = serial_no_z 
        self.serial_no_x = serial_no_x
        self.serial_no_y = serial_no_y
        self.motor_z = None
        self.motor_x = None
        self.motor_y = None

    def ConnectMotor(self, serial_no):
        motor = KCubeDCServo.CreateKCubeDCServo(serial_no)

        # If Serial Number is assigned connect motor
        if not motor == None:
            motor.Connect(serial_no)

            # Wait for the device settings to initialize
            if not motor.IsSettingsInitialized():
                motor.WaitForSettingsInitialized(5000)  # 5 seconds timeout
                assert motor.IsSettingsInitialized() is True

            # Start Polling the Device
            motor.StartPolling(50)
            time.sleep(.1)

            # Enable the device
            motor.EnableDevice()
            time.sleep(.1)

            # Load and Update motor configuration
            config = motor.LoadMotorConfiguration(serial_no, DeviceConfiguration.DeviceSettingsUseOptionType.UseFileSettings)
            if serial_no == self.serial_no_z:
                config.DeviceSettingsName = str('DDSO50')    #
            else:
                config.DeviceSettingsName = str('MTS50-Z8')
            config.UpdateCurrentConfiguration()
            motor.SetSettings(motor.MotorDeviceSettings, True, False)

            # Load and Update motor 
            # Home the device
            print(f"Homing device {serial_no}...")
            motor.Home()
        
        # Else Quit program
        else:
            quit()
        return motor

    def ConnectAllMotors(self):
        self.motor_z = self.ConnectMotor(self.serial_no_z)
        self.motor_x = self.ConnectMotor(self.serial_no_x)
        self.motor_y = self.ConnectMotor(self.serial_no_y)

    def SetVelocityParams(self, max_velocity, acceleration):
        vel_params = self.motor.GetVelocityParams()
        vel_params.MaxVelocity = max_velocity
        vel_params.Acceleration = acceleration
        self.motor.SetVelParams(vel_params)
        print(f"Velocity parameters set: Max Velocity={max_velocity} mm/s, Acceleration={acceleration} mm/s^2")

    def SetJogParams(self, motor, step_size):
        jog_params = motor.GetJogParams()
        jog_params.StepSize = step_size
        jog_params.JogVelocity = Decimal(2.4)
        jog_params.JogAcceleration = Decimal(1.5)
        jog_params.JogMode = JogParametersBase.JogModes.SingleStep
        motor.SetJogParams(jog_params)
        print(f"Jog parameters set: Step Size={step_size} mm, Velocity=2.4 mm/s, Acceleration=1.5 mm/s^2, Mode=SingleStep")

    def SetMotorParams(self, stop_mode, backlash_distance):
        motor_params = self.motor.GetMotorParams()
        motor_params.StopMode = stop_mode
        motor_params.BacklashCompensation = backlash_distance
        self.motor.SetMotorParams(motor_params)
        print(f"Motor parameters set: Stop Mode={stop_mode}, Backlash Distance={backlash_distance} mm")

    def SetAllParameters(self, step_size):
        self.SetJogParams(self.motor_z, step_size)
        self.SetJogParams(self.motor_x, step_size)
        self.SetJogParams(self.motor_y, step_size)

    def MoveMotor(self, motor, position, axis_name):
        print(f"Moving {axis_name} axis to position {position}...")
        motor.MoveJog(position, 60000)  # 60 seconds timeout

        # Wait for the device to complete the move
        while motor.Status.IsMoving:
            time.sleep(0.1)  # Check every 100ms
        
        print(f"{axis_name} axis move completed.")

    def MoveAllMotors(self, position_x, position_y):
        self.MoveMotor(self.motor_x, position_x, "X")
        self.MoveMotor(self.motor_y, position_y, "Y")

    def DisconnectMotor(self, motor):
        motor.StopPolling()
        motor.Disconnect(False)

    def DisconnectAllMotors(self):
        self.DisconnectMotor(self.motor_z)
        self.DisconnectMotor(self.motor_x)
        self.DisconnectMotor(self.motor_y)







