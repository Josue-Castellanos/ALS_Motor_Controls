import KCube_Controller



def main():
    """
        The main entry point of the application
        
    """
    try:
        # Usage example
        serial_no_x = str('27263196')
        serial_no_y = str('27263127') 

        mask_motor = KCube_Controller.MaskMotor(serial_no_x, serial_no_y)
        mask_motor.ConnectAllMotors()

        mask_motor.SetAllParameters(step_size=0.050)

        # Move all motors to specified positions
        position_x = 21.84173 # Target position for X axis in device units
        position_y = 20.60000  # Target position for Y axis in device units

        mask_motor.MoveAllMotors(position_x, position_y)

        # Disconnect all motors
        mask_motor.DisconnectAllMotors()

    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()