import time
import clr 

# Add reference to the Thorlabs Kinesis DLLs (Dynaimic-Link Libraries)
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.KCube.DCServoCLI.dll")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.KCube.BrushlessMotorCLI.dll")

# Import the namespaces from the Thorlabs Kinesis DLLs
from Thorlabs.MotionControl.DeviceManagerCLI import *         
from Thorlabs.MotionControl.GenericMotorCLI import *            
from Thorlabs.MotionControl.GenericMotorCLI.ControlParameters import JogParametersBase
from Thorlabs.MotionControl.KCube.DCServoCLI import *  
from Thorlabs.MotionControl.KCube.BrushlessMotorCLI import *         
from System import Decimal

# Initialize the DeviceManager
DeviceManagerCLI.BuildDeviceList()

# 
class MaskMotor:
    def __init__(self, serial_no_x, serial_no_y, serial_no_z):
        self.serial_no_x = serial_no_x
        self.serial_no_y = serial_no_y
        self.serial_no_z = serial_no_z
        self.motor_x = None
        self.motor_y = None
        self.motor_z = None

    def ConnectMotor(self, serial_no):
        try:
            if serial_no == str('28252438'):
                motor = KCubeBrushlessMotor.CreateKCubeBrushlessMotor(serial_no)
            else:
                motor = KCubeDCServo.CreateKCubeDCServo(serial_no)

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
                    config = motor.LoadMotorConfiguration(serial_no, DeviceConfiguration.DeviceSettingsUseOptionType.UseDeviceSettings)
                    config.DeviceSettingsName = str('DDS050') # Optics stage 
                else:
                    config = motor.LoadMotorConfiguration(serial_no, DeviceConfiguration.DeviceSettingsUseOptionType.UseFileSettings)
                    config.DeviceSettingsName = str('MTS50-Z8') # Mask Stage
                config.UpdateCurrentConfiguration()
                motor.SetSettings(motor.MotorDeviceSettings, True, False)
            
        except Exception as e:
            print(e)
        return motor

    def ConnectAllMotors(self):
        self.motor_x = self.ConnectMotor(self.serial_no_x)
        self.motor_y = self.ConnectMotor(self.serial_no_y)
        self.motor_z = self.ConnectMotor(self.serial_no_z)

    def SetVelocityParams(self, motor, max_velocity, acceleration):
        vel_params = motor.GetVelocityParams()
        vel_params.MaxVelocity = max_velocity
        vel_params.Acceleration = acceleration
        motor.SetVelParams(vel_params)
        print(f"Velocity parameters set: Max Velocity={max_velocity} mm/s, Acceleration={acceleration} mm/s^2")

    def SetJogParams(self, motor, step_size):
        jog_params = motor.GetJogParams()
        jog_params.StepSize = Decimal(step_size)
        jog_params.JogVelocity = Decimal(2)
        jog_params.JogAcceleration = Decimal(1)
        jog_params.JogMode = JogParametersBase.JogModes.SingleStep
        motor.SetJogParams(jog_params)
        print(f"Jog parameters set: Step Size={step_size} mm, Velocity=2.4 mm/s, Acceleration=1.5 mm/s^2, Mode=SingleStep")

    def SetMotorParams(self, motor, stop_mode, backlash_distance):
        motor_params = motor.GetMotorParams()
        motor_params.StopMode = stop_mode
        motor_params.BacklashCompensation = backlash_distance
        motor.SetMotorParams(motor_params)
        print(f"Motor parameters set: Stop Mode={stop_mode}, Backlash Distance={backlash_distance} mm")

    def SetAllParameters(self, step_size):
        self.SetJogParams(self.motor_x, step_size)
        self.SetJogParams(self.motor_y, step_size)
        self.SetJogParams(self.motor_z, step_size)

    def MoveMotor(self, motor, position, axis_name):
        print(f"Moving {axis_name} axis to position {position}...")
        motor.MoveTo(Decimal(position), 60000)  # 60 seconds timeout in milliseconds

        # Wait for the device to complete the move
        while motor.Status.IsMoving:
            time.sleep(0.1)  # Check every 100ms
        print(f"{axis_name} axis move completed.")

    def MoveAllMotors(self, position_x, position_y, position_z):
        self.MoveMotor(self.motor_x, position_x, "X")
        self.MoveMotor(self.motor_y, position_y, "Y")
        self.MoveMotor(self.motor_z, position_z, "Z")

    def ForwardJogMotor(self, motor):
        print(f"Jogging Forward with step size (enter step size here)...")
        motor.MoveJog(MotorDirection.Forward, 60000) # Wait time in milliseconds

    def JogAllMotors(self):
        self.ForwardJogMotor(self.motor_z)

    def DisconnectMotor(self, motor):
        motor.StopPolling()
        motor.Disconnect(False)

    def DisconnectAllMotors(self):
        self.DisconnectMotor(self.motor_x)
        self.DisconnectMotor(self.motor_y)
        self.DisconnectMotor(self.motor_z)







