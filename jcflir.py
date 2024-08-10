"""
    Josue B. Castellanos 
    6/17/24 -- 8/6/24
    https://github.com/Josue-Castellanos/ALS_Motor_Controls
    (c) Lawrence Berkelay National Laboratory, 2024
    python file: jcflir.py

    **This version is only compatible with PySpin for Spinnaker 3.0.0.118 and Python 3.10**
    **If your Matlab/LabView supports newer versions of Spinnaker (like 3.2.0.62)**
    **I would recommend updating to that version, for both Spinnaker/PySpin**
"""
import numpy as np
import PySpin
import psutil
import socket
import time
import subprocess
import ctypes
import datetime
    
class StreamMode:
    """
    'Enum' for choosing stream mode
    """
    STREAM_MODE_TELEDYNE_GIGE_VISION = 0  # Teledyne Gige Vision stream mode is the default stream mode for spinview which is supported on Windows
    STREAM_MODE_PGRLWF = 1  # Light Weight Filter driver is our legacy driver which is supported on Windows
    STREAM_MODE_SOCKET = 2  # Socket is supported for MacOS and Linux, and uses native OS network sockets instead of a filter driver


class Camera:
    def __init__(self, log_signal=None):
        # Retrieve singleton reference to system object
        self.system = PySpin.System.GetInstance()
        self.cam = None
        self.cam_list = None
        self.processor = None
        self.log_signal = log_signal if log_signal else print

    def log(self, level, component, message, details=""):
        self.log_signal(level, component, message, details)

    def ConnectCamera(self):
        self.log("INFO", "Camera", "Checking if system is in use...")
        inUse = self.system.IsInUse()

        if inUse:
            self.system.ReleaseInstance()
            self.log("WARNING", "Camera", "The system is in use...")
            return None
        
        self.log("INFO", "Camera", "Checking Library version from system...")
        version = self.system.GetLibraryVersion()
        self.log("INFO", "Camera", "Library version", f"{version.major}.{version.minor}.{version.type}.{version.build}")

        self.cam_list = self.system.GetCameras()
        self.log("INFO", "Camera", "Camera list retrieved...")

        if self.cam_list == 0:
            self.log("ERROR", "Camera", "Camera list is empty!")
            return

        num_cameras = self.cam_list.GetSize()
        self.log("INFO", "Camera", f"Number of Cameras in list: {num_cameras}")

        if num_cameras == 0:
            self.cam_list.Clear()
            self.system.ReleaseInstance()
            self.log("ERROR", "Camera", "No Cameras detected...")
            return None
        
        self.log("INFO", "Camera", "Selecting the first Camera...")
        self.cam = self.cam_list[0]
        self.RunSingleCamera()
        
        # Set buffer handling mode to NewestOnly
        sNodemap = self.cam.GetTLStreamNodeMap()
        node_bufferhandling_mode = PySpin.CEnumerationPtr(sNodemap.GetNode('StreamBufferHandlingMode'))
        if PySpin.IsReadable(node_bufferhandling_mode) and PySpin.IsWritable(node_bufferhandling_mode):
            node_newestonly = node_bufferhandling_mode.GetEntryByName('NewestOnly')
            if PySpin.IsReadable(node_newestonly):
                node_newestonly_mode = node_newestonly.GetValue()
                node_bufferhandling_mode.SetIntValue(node_newestonly_mode)
                self.log("INFO", "Camera", "Buffer handling mode set to NewestOnly")

        # Set acquisition mode to continuous
        nodemap = self.cam.GetNodeMap()
        node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
        if PySpin.IsReadable(node_acquisition_mode) and PySpin.IsWritable(node_acquisition_mode):
            node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
            if PySpin.IsReadable(node_acquisition_mode_continuous):
                acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
                node_acquisition_mode.SetIntValue(acquisition_mode_continuous)
                self.log("INFO", "Camera", "Acquisition mode set to continuous")

        self.cam.BeginAcquisition()

    def DisconnectCamera(self):
        if hasattr(self, 'cam'):
            try:
                self.cam.EndAcquisition()
                self.cam.DeInit()
                del self.cam
            except PySpin.SpinnakerException as ex:
                self.log("ERROR", "Camera", "Error disconnecting camera", str(ex))
        
        if hasattr(self, 'cam_list'):
            self.cam_list.Clear() 
            
        self.system.ReleaseInstance()
        self.log("INFO", "Camera", "Camera disconnected and resources released")


    def SetStreamMode(self):
        """
        This function changes the stream mode

        :param cam: Camera to change stream mode.
        :type cam: CameraPtr
        :type nodemap_tlstream: INodeMap
        :return: True if successful, False otherwise.
        :rtype: bool
        """
        streamMode = "TeledyneGigeVision"

        result = True
        nodemap_tlstream = self.cam.GetTLStreamNodeMap()
        node_stream_mode = PySpin.CEnumerationPtr(nodemap_tlstream.GetNode('StreamMode'))

        if PySpin.IsReadable(node_stream_mode) and PySpin.IsWritable(node_stream_mode):
            node_stream_mode_custom = PySpin.CEnumEntryPtr(node_stream_mode.GetEntryByName(streamMode))
            if PySpin.IsReadable(node_stream_mode_custom):
                stream_mode_custom = node_stream_mode_custom.GetValue()
                node_stream_mode.SetIntValue(stream_mode_custom)
                self.log("INFO", "Camera", f"Stream Mode set to {node_stream_mode.GetCurrentEntry().GetSymbolic()}")
        return result


    def AcquireImage(self, point, filename=None):
        """
        This function acquires and saves 10 images from a device.

        :param cam: Camera to acquire images from.
        :param nodemap: Device nodemap.
        :param nodemap_tldevice: Transport layer device nodemap.
        :type cam: CameraPtr
        :type nodemap: INodeMap
        :type nodemap_tldevice: INodeMap
        :return: True if successful, False otherwise.
        :rtype: bool
        """

        self.log("INFO", "Camera", "Capturing high-quality image")
        try:
            image_result = self.cam.GetNextImage(1000)
            if image_result.IsIncomplete():
                self.log("WARNING", "Camera", f"Image incomplete with image status {image_result.GetImageStatus()}")
                return None
            else:
                self.processor = PySpin.ImageProcessor()
                self.processor.SetColorProcessing(PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR)
                
                # Convert to high-quality format (you can adjust based on your needs)
                image_converted = self.processor.Convert(image_result, PySpin.PixelFormat_RGB16)
                
                """ 
                    ====================================
                    We Can implement our save logic here
                    ====================================

                """
                # date_series_point.png
                # 240721_0001_001.png
                filename = 'Image Single Scan %d.png' % point
                if filename:
                    image_converted.Save(filename)
                    self.log("INFO", "Camera", f"High-quality image saved", filename)

                
                # width = image_converted.GetWidth()
                # height = image_converted.GetHeight()
                image_data = image_converted.GetNDArray()

                image_result.Release()
                return image_data

        except PySpin.SpinnakerException as ex:
            self.log("ERROR", "Camera", "Error capturing high-quality image", str(ex))
            return None


    def PrintDeviceInfo(self, nodemap_tldevice):
        """
        This function prints the device information of the camera from the transport
        layer; please see NodeMapInfo example for more in-depth comments on printing
        device information from the nodemap.

        :param nodemap: Transport layer device nodemap.
        :type nodemap: INodeMap
        :returns: True if successful, False otherwise.
        :rtype: bool
        """
        self.log("INFO", "Camera", "Retrieving device information")
        try:
            result = True
            node_device_information = PySpin.CCategoryPtr(nodemap_tldevice.GetNode('DeviceInformation'))

            if PySpin.IsReadable(node_device_information):
                features = node_device_information.GetFeatures()
                for feature in features:
                    node_feature = PySpin.CValuePtr(feature)
                    if PySpin.IsReadable(node_feature):
                        self.log("INFO", "CameraInfo", f"{node_feature.GetName()}", node_feature.ToString())
                    else:
                        self.log("WARNING", "CameraInfo", f"{node_feature.GetName()}", "Node not readable")
            else:
                self.log("WARNING", "Camera", "Device control information not readable")

        except PySpin.SpinnakerException as ex:
            self.log("ERROR", "Camera", "Error retrieving device information", str(ex))
            return False

        return result


    def RunSingleCamera(self):
        """
        This function acts as the body of the example; please see NodeMapInfo example
        for more in-depth comments on setting up cameras.

        :param cam: Camera to run on.
        :type cam: CameraPtr
        :return: True if successful, False otherwise.
        :rtype: bool
        """
        try:
            result = True
            nodemap_tldevice = self.cam.GetTLDeviceNodeMap()
            result &= self.PrintDeviceInfo(nodemap_tldevice)
            self.cam.Init()
            # result &= self.SetStreamMode()
            self.log("INFO", "Camera", "Camera initialized and stream mode set")
        except PySpin.SpinnakerException as ex:
            self.log("ERROR", "Camera", "Error in RunSingleCamera", str(ex))
            result = False
        return result
    

    def GetFrame(self):
        try:
            image_result = self.cam.GetNextImage(1000)
            if image_result.IsIncomplete():
                self.log("WARNING", "Camera", f"Image incomplete with image status {image_result.GetImageStatus()}")
                return None, None, None
            else:
                width = image_result.GetWidth()
                height = image_result.GetHeight()
                self.processor = PySpin.ImageProcessor()
                self.processor.SetColorProcessing(PySpin.SPINNAKER_COLOR_PROCESSING_ALGORITHM_HQ_LINEAR)
                image_converted = self.processor.Convert(image_result, PySpin.PixelFormat_RGB8)
                image = image_converted.GetData().reshape(height, width, 3)
                image_result.Release()
                return image, width, height
        except PySpin.SpinnakerException as ex:
            self.log("ERROR", "Camera", "Error acquiring frame", str(ex))
            return None, None, None

    # Maybe I can pass nodemap?
    def SetGain(self, gain_value):
        try:
            nodemap = self.cam.GetNodeMap()
            node_gain = PySpin.CFloatPtr(nodemap.GetNode("Gain"))

            # This might not pass becasue if write
            if not PySpin.IsReadable(node_gain) or not PySpin.IsWritable(node_gain):
                self.log("ERROR", "Camera", "Unable to set gain node")

            # Get the minimum and maximum allowable gain values
            gain_min = node_gain.GetMin()
            gain_max = node_gain.GetMax()

            # Ensure the gain value is within the allowable range
            if gain_value < gain_min or gain_value > gain_max:
                self.log("WARNING", "Camera", f"Gain value {gain_value} is out of range", f"Adjust to fit within {gain_min} - {gain_max}.")
                gain_value = max(min(gain_value, gain_max), gain_min)
                
            node_gain.SetValue(gain_value)
            self.log("INFO", "Camera", f"Gain set to {gain_value}")
            return True
        except PySpin.SpinnakerException as ex:
            self.log("ERROR", "Camera", "Error setting gain", str(ex))
            return False
    
    def SetExposureTime(self, exposure_time):
        try:
            nodemap = self.cam.GetNodeMap()
            node_exposure_auto = PySpin.CEnumerationPtr(nodemap.GetNode("ExposureAuto"))
            if PySpin.IsReadable(node_exposure_auto) and PySpin.IsWritable(node_exposure_auto):
                node_exposure_auto_off = node_exposure_auto.GetEntryByName("Off")
                if PySpin.IsReadable(node_exposure_auto_off):
                    exposure_auto_off_value = node_exposure_auto_off.GetValue()
                    node_exposure_auto.SetIntValue(exposure_auto_off_value)

            node_exposure_time = PySpin.CFloatPtr(nodemap.GetNode("ExposureTime"))
            if not PySpin.IsReadable(node_exposure_time) or not PySpin.IsWritable(node_exposure_time):
                self.log("ERROR", "Camera", "Unable to set exposure time")
                return False
            
            # Get the minimum and maximum allowable exposure time values
            exposure_min = node_exposure_time.GetMin()
            exposure_max = node_exposure_time.GetMax()

            if exposure_time < exposure_min or exposure_time > exposure_max:
                self.log("WARNING", "Camera", f"Exposure time value {exposure_time} is out of range", f"Adjust to fit within {exposure_min} - {exposure_max}")
                exposure_time = max(min(exposure_time, exposure_max), exposure_min)
            
            # We can check if the exposure time we want is within the limits or not
            node_exposure_time.SetValue(exposure_time)
            self.log("INFO", "Camera", f"Exposure time set to {exposure_time} microseconds")
            return True
        except PySpin.SpinnakerException as ex:
            self.log("ERROR", "Camera", "Error setting exposure time", str(ex))
            return False
        
    def SetCameraSettings(self, gain_value, exposure_time):
        self.log("INFO", "Camera", "Configuring camera settings")

        if not self.SetGain(gain_value):
            self.log("ERROR", "Camera", "Failed to set gain")
            return False
        
        if not self.SetExposureTime(exposure_time):
            self.log("ERROR", "Camera", "Failed to set exposure time")
            return False

        self.log("INFO", "Camera", "Camera settings configured")
        return True