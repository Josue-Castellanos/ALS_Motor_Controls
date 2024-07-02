import jckcube
import jcflir
import ctypes
import sys

# 
def main():
    """
        The main entry point of the application
        
    """
    try:
        if jcflir.IsAdmin():
            # Usage example
            serial_no_x = str('27263196')
            serial_no_y = str('27263127') 
            serial_no_z = str('28252438')  
            cam_ip = str('192.168.10.1')
            interface_ip = str('192.168.10.200')
            
            cam = jcflir.Camera(cam_ip, interface_ip)
            cam.ConnectCamera()
            
            mask_motor = jckcube.MaskMotor(serial_no_x, serial_no_y, serial_no_z)
            mask_motor.ConnectAllMotors()
            
            # mask_motor.SetAllParameters(step_size=0.050) # millimeters

            ## Move all motors to specified positions
            # position_x = 21.84173 # Target position for X axis in device units
            # position_y = 20.60000  # Target position for Y axis in device units
            # position_z = 5.00000  # Target position for Z axis in device units
            # mask_motor.MoveAllMotors(position_x, position_y, position_z)

            mask_motor.JogAllMotors()

            # Disconnect all motors
            mask_motor.DisconnectAllMotors()
        else:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, ' '.join(sys.argv), None, 1)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()