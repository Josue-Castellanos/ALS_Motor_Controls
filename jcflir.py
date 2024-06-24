import PySpin



class Camera:
    def ConnectCamera():
        # Setup Camera
        # Retrieve singleton reference to system object
        system = PySpin.System.GetInstance()

        # Retrieve list of cameras from the system
        cam_list = system.GetCameras()

        num_cameras = cam_list.GetSize()

        if num_cameras == 0:
            # Clear camera list before releasing system
            cam_list.Clear()
            # Release system instance
            system.ReleaseInstance()
            print('No cameras detected.')
            return None
        # Select first camera 
        cam = cam_list.GetByIndex(0) 
        try: 
            # Initialize camera 
            cam.Init()

            # Retrieve device information
            nodemap_tldevice = cam.GetTLDeviceNodeMap() 
            node_device_information = PySpin.CCategoryPtr(nodemap_tldevice.GetNode('DeviceInformation'))

            if PySpin.IsAvailable(node_device_information) and PySpin.IsReadable(node_device_information): 
                features = node_device_information.GetFeatures() 
                
                for feature in features: 
                    node_feature = PySpin.CValuePtr(feature) 
                    print(f'{node_feature.GetName()}: {node_feature.ToString()}') 
            
            # Acquire images 
            cam.BeginAcquisition()

            for i in range(10): 
                image_result = cam.GetNextImage() 

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
                    
            cam.EndAcquisition() 
                    
            # Deinitialize camera 
            cam.DeInit() 
        except PySpin.SpinnakerException as ex: 
            print(f'Error: {ex}') 
            
        finally:
            # Release camera 
            del cam 

            # Clear camera list before releasing system 
            cam_list.Clear() 
            
            # Release system instance 
            system.ReleaseInstance()
