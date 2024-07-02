import numpy as np
import PySpin
import psutil
import socket
import time
import subprocess
import ctypes

def IsAdmin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False
    
class Camera:
    def __init__(self, cam_ip_address, interface_ip_address):
        # Retrieve singleton reference to system object
        self.system = PySpin.System.GetInstance()
        self.cam = None
        self.cam_ip_address = cam_ip_address
        self.interface_ip_address = interface_ip_address
        self.interface = None

    def GetLocalInterfaces(self):
        interfaces = psutil.net_if_addrs()
        interface_map = {}
        for interface, addresses in interfaces.items():
            for address in addresses:
                if address.family == socket.AF_INET:
                    interface_map[interface] = address.address
                    print(f"Interface: {interface}, IPv4 Address: {address.address}")
        return interface_map
        
    def SetRoute(self):
        try:  
            # Command to add a route on Windows
            command = f"route add {self.cam_ip_address} mask 255.255.255.0 {self.interface_ip_address}"
            print(command)
            # Run the command with elevated privileges
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            # Check for errors
            if result.returncode != 0:
                print(f"Error: {result.stderr}")
            else:
                print(f"Success: {result.stdout}")
                
        except Exception as e:
            print(f"An error occurred: {e}")

    def ConnectCamera(self):
        # Get Network Interfaces
        print("Network Interfaces:")
        interfaces = self.GetLocalInterfaces()

        if self.interface_ip_address not in interfaces.values():
            print(f"Interface IP address {self.interface_ip_address} not found")
            return

        # Set route for communication to the camera
        self.SetRoute()

        # Setup Camera
        print('Checking if system is in use...')
        inUse = self.system.IsInUse()

        if inUse:
            self.system.ReleaseInstance()
            print('The system is in use...')
            return None
        print('Check Library version from system...')
        version = self.system.GetLibraryVersion()
        print('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

        # Retrieve list of interfaces from the system
        interface_list = self.system.GetInterfaces()
        if interface_list is not None:
            print('Interface list retrieved...') 

        num_interfaces = interface_list.GetSize()
        print(f'Number of Interfaces in list: {num_interfaces}')

        if num_interfaces == 0:
            # Clear interface list before releasing system
            interface_list.Clear()
            # Release system instance
            self.system.ReleaseInstance()
            print('No Interfaces detected')
            return None
        
        # Select first interface 
        print('Select the first Interface...')
        interface = interface_list.GetByIndex(0)
        print(interface)

        # Create camera object
        # Retrieve list of cameras from the system
        cam_list = self.system.GetCameras()
        print('Camera list retrieved...')

        if cam_list == 0:
            print("Camera list is empty!")
            return

        num_cameras = cam_list.GetSize()
        print(f'Number of Cameras in list: {num_cameras}')

        if num_cameras == 0:
            # Clear camera list before releasing system
            cam_list.Clear()
            # Release system instance
            self.system.ReleaseInstance()
            print('No Cameras detected...')
            return None
        
        # Select first camera
        print('Select the first Camera...')
        self.cam = cam_list.GetByIndex(0)

        time.sleep(30)
        try: 
            # Initialize camera 
            print('Initializing camera...')
            self.cam.Init()

            # Retrieve device information
            nodemap_tldevice = self.cam.GetTLDeviceNodeMap() 
            node_device_information = PySpin.CCategoryPtr(nodemap_tldevice.GetNode('DeviceInformation'))

            if PySpin.IsAvailable(node_device_information) and PySpin.IsReadable(node_device_information): 
                features = node_device_information.GetFeatures() 
                
                for feature in features: 
                    node_feature = PySpin.CValuePtr(feature) 
                    print(f'{node_feature.GetName()}: {node_feature.ToString()}') 
            
            # Acquire images 
            self.cam.BeginAcquisition()

            for i in range(10): 
                image_result = self.cam.GetNextImage() 

                if image_result.IsIncomplete(): 
                    print(f'Image incomplete with image status {image_result.GetImageStatus()}') 
                else: 
                    width = image_result.GetWidth() 
                    height = image_result.GetHeight() 
                    print(f'Grabbed Image {i}, width = {width}, height = {height}') 
                    
                    # Save image 
                    filename = f'Image-{i}.jpg' 
                    image_result.Save(filename) 
                    print(f'Image saved at {filename}') 
                
                image_result.Release() 
                    
            self.cam.EndAcquisition() 
                    
            # Deinitialize camera 
            self.cam.DeInit() 
        except PySpin.SpinnakerException as ex: 
            print(f'Error: {ex}') 
            
        finally:
            # Release camera 
            del self.cam 

            # Clear interface list before releasing system 
            interface_list.Clear() 
            
            # Release system instance 
            self.system.ReleaseInstance()
