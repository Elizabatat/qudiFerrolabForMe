# -*- coding: utf-8 -*-

"""
The Imagining Source camera: DMK 33UX264
config:camera.TIS.DMK_33UX264.UsbCamera

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

'''
Needed DLLs for 64 bit environment are
- tisgrabber_x64.dll
- TIS_UDSHL11_x64.dll
'''
import time
import ctypes
import numpy as np
import cv2 as cv2
import hardware.camera.TIS.tisgrabber as tis
from qtpy import QtCore
from core.module import Base
from core.configoption import ConfigOption
from interface.camera_interface import CameraInterface

class CallbackUserdata(ctypes.Structure):
    """ Example for user data passed to the callback function. """
    def __init__(self):
        self.width = 0
        self.height = 0
        self.BytesPerPixel = 0
        self.buffer_size = 0
        self.oldbrightness = 0
        self.getNextImage = 0
        self.cvMat = None



class UsbCamera(Base, CameraInterface):
    ic = ctypes.cdll.LoadLibrary("D:/qudiFerroLab/hardware/camera/TIS/tisgrabber_x64.dll")
    tis.declareFunctions(ic)

    ic.IC_InitLibrary(0)
    hGrabber = ic.IC_CreateGrabber()
    _camera_name = 'DMK 33UX264'

    _exposure = ctypes.c_long()
    _gain = ctypes.c_long()
    _ud = None
    #sig=QtCore.Signal()
    #UserData = CallbackUserdata()
    # _fps = None


    # _width = ctypes.c_long()
    # _height = ctypes.c_long()
    # _colorformat = ctypes.c_int()
    # _BitsPerPixel = ctypes.c_int()
    # _bpp = None
    # _resolution = None
    _data = None
    # _acquiring = False
    # _live = False
    # imagedata= None

    def on_activate(self):
        """ Initialisation performed during activation of the module.
       """
        self.hGrabber = self.ic.IC_ShowDeviceSelectionDialog(None)  # for fine tuning
        self.ic.IC_OpenVideoCaptureDevice(self.hGrabber, tis.T(self._camera_name))
        #self.Callbackfunc = self.ic.FRAMEREADYCALLBACK(self.FrameCallback)
        #self.ic.IC_StopLive(self.hGrabber)
        #self.ic.IC_StartLive(self.hGrabber, 1)


    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.ic.IC_StopLive(self.hGrabber)
        self.ic.IC_ReleaseGrabber(self.hGrabber)
        _acquiring = False
        _live = False

    def get_name(self):
        """ Retrieve an identifier of the camera that the GUI can print
        @return string: name for the camera
        """
        return self._camera_name

    def FrameCallback(self, pBuffer, framenumber, pData):
        """ This is an example callback function for image processing  with
            OpenCV
        :param: hGrabber: This is the real pointer to the grabber object.
        :param: pBuffer : Pointer to the first pixel's first byte
        :param: framenumber : Number of the frame since the stream started
        :param: pData : Pointer to additional user data structure
        """

        if pData.buffer_size > 0:
            image = ctypes.cast(pBuffer, ctypes.POINTER(ctypes.c_ubyte * pData.buffer_size))

            pData.cvMat = np.ndarray(buffer=image.contents,
                                     dtype=np.uint8,
                                     shape=(pData.height.value,
                                            pData.width.value,
                                            pData.BytesPerPixel))


    Callbackfunc = ic.FRAMEREADYCALLBACK(FrameCallback)
    UserData = CallbackUserdata()


    def CreateUserData(self):
        ''' Create the user data for callback for the passed camera
        :param ud User data to create
        :param camera The camera connected to the user data
        '''

        self.UserData.width = ctypes.c_long()
        self.UserData.height = ctypes.c_long()
        iBitsPerPixel = ctypes.c_int()
        colorformat = ctypes.c_int()

        # Query the values
        self.ic.IC_GetImageDescription(self.hGrabber, self.UserData.width, self.UserData.height, iBitsPerPixel, colorformat)

        self.UserData.BytesPerPixel = int(iBitsPerPixel.value / 8.0)
        self.UserData.buffer_size = self.UserData.width.value * self.UserData.height.value * self.UserData.BytesPerPixel
        self.UserData.getNextImage = 0

    def startCamera(self):
        '''Start the passed camera
        :param UserData user data connected with the camera
        :param Camera The camera to start
        '''

        self.ic.IC_SetContinuousMode(self.hGrabber, 0)
        self.ic.IC_StartLive(self.hGrabber, 0)
        self.CreateUserData()
        self.ic.IC_SetFrameReadyCallback(self.hGrabber, self.Callbackfunc, self.UserData)

    def get_size(self):
        """ Retrieve size of the image in pixel
        @return tuple: Size (width, height)
        """

        self._resolution = (
            self.ic.IC_GetVideoFormatWidth(self.hGrabber), self.ic.IC_GetVideoFormatHeight(self.hGrabber))

        return self._resolution

    def support_live_acquisition(self):
        """ Return whether the camera can take care of live acquisition
        @return bool: True if supported, False if not
        """
        return True

    def start_live_acquisition(self):
        """ Start a continuous acquisition

        @return bool: Success ?
        """
        """
                Set the camera in live mode
                """
        pass

    def start_single_acquisition(self):
        pass
    #     """ Start a single acquisition
    #     @return bool: Success ?
    #     """
    #
    #     self._acquiring = True
    #     self.take_frame()
    #     time.sleep(float(100 / 10000))
    #     self._acquiring = False



    def stop_acquisition(self):
        """ Stop/abort live or single acquisition

        @return bool: Success ?
        """
        #if self.ic.IC_IsDevValid(self.hGrabber):
        self.free = False
        self.ic.IC_StopLive(self.hGrabber)
        self._live = False
        self._acquiring = False

    # def take_frame(self):
    #     """ Return an array of last acquired image.
    #
    #     @return numpy array: image data in format [[row],[row]...]
    #
    #     Each pixel might be a float, integer or sub pixels
    #     """
    #     if self.ic.IC_IsDevValid(self.hGrabber):
    #         self.ic.IC_StartLive(self.hGrabber, 0)
    #         if self.ic.IC_SnapImage(self.hGrabber, 2000) == tis.IC_SUCCESS:
    #             self.ic.IC_GetImageDescription(self.hGrabber, self._width, self._height,
    #                                            self._BitsPerPixel, self._colorformat)
    #             # # Calculate the buffer size
    #             self._bpp = int(self._BitsPerPixel.value / 8.0)
    #             buffer_size = self._width.value * self._height.value * self._BitsPerPixel.value
    #             # # Get the image data
    #             imagePtr = self.ic.IC_GetImagePtr(self.hGrabber)
    #             self.imagedata = ctypes.cast(imagePtr, ctypes.POINTER(ctypes.c_ubyte * buffer_size))
    #             # # Create the numpy array
    #             self._data = np.ndarray(buffer=self.imagedata.contents, dtype=np.uint8,
    #                                     shape=(self._height.value, self._width.value, self._bpp))
    #
    #         self.ic.IC_StopLive(self.hGrabber)
    #     #return self._data

    # def take_video_frame(self):
    #     """
    #     """
    #     if self.ic.IC_IsDevValid(self.hGrabber):
    #         self.ic.IC_SetVideoFormat(self.hGrabber, tis.T("Y16 (1920x1024)"))
    #         self.ic.IC_SetFrameRate(self.hGrabber, ctypes.c_float(30.0))
    #
    #         self.ic.IC_StartLive(self.hGrabber, 1)
    #         self.ic.IC_StartLive(self.hGrabber, 1)


    def get_acquired_data(self):
        """ Return an array of last acquired image.

        @return numpy array: image data in format [[row],[row]...]

        Each pixel might be a float, integer or sub pixels
        """
        return    self.UserData.cvMat #self._data

    def set_exposure(self, exposure):
        """ Set the exposure time in seconds
        @param float time: desired new exposure time
        @return float: setted new exposure time
        """
        if self.ic.IC_IsDevValid(self.hGrabber):
            self.ic.IC_SetPropertyAbsoluteValue(self.hGrabber, tis.T("Exposure"), tis.T("Value"),
                                                ctypes.c_float(exposure))
            self._exposure = exposure

        return self._exposure

    def get_exposure(self):
        """ Get the exposure time in seconds
            @return float exposure time
            """
        if self.ic.IC_IsDevValid(self.hGrabber):
            self.ic.IC_GetPropertyValue(self.hGrabber, tis.T("Exposure"), tis.T("Value"),
                                        self._exposure)
        return abs(self._exposure.value)

    def set_gain(self, gain):
        """ Set the gain
        @param float gain: desired new gain
        @return float: new exposure gain
        """
        if self.ic.IC_IsDevValid(self.hGrabber):
            self.ic.IC_SetPropertyValue(self.hGrabber, tis.T("Gain"), tis.T("Value"), ctypes.c_float(gain))
            self._gain = gain.value
        return self._gain

    def get_gain(self):
        """ Get the gain
        @return float: exposure gain
        """
        if self.ic.IC_IsDevValid(self.hGrabber):
            self.ic.IC_GetPropertyValue(self.hGrabber, tis.T("Gain"), tis.T("Value"), self._gain)
        return self._gain.value

    def get_ready_state(self):
        """
             Return whether or not the camera is ready for an acquisition
             """
        if self.ic.IC_IsDevValid(self.hGrabber):
            return False
        else:
            print("No device opened,")
        return not (self._live or self._acquiring)
