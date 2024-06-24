import jckcube
import jcflir


# 
def main():
    """
        The main entry point of the application
        
    """
    try:
        # Usage example
        serial_no_z = str('28252438')
        serial_no_x = str('27263196')
        serial_no_y = str('27263127') 

        mask_motor = jckcube.MaskMotor(serial_no_x, serial_no_y, serial_no_z)
        mask_motor.ConnectAllMotors()
        
        cam = jcflir.Camera()
        mask_motor.SetAllParameters(step_size=0.050) # millimeters

        # Move all motors to specified positions
        # position_x = 21.84173 # Target position for X axis in device units
        # position_y = 20.60000  # Target position for Y axis in device units
        # position_z = 5.00000  # Target position for Z axis in device units
        # mask_motor.MoveAllMotors(position_x, position_y, position_z)

        mask_motor.JogALLMotors()

        # Disconnect all motors
        mask_motor.DisconnectAllMotors()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()