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
import hardware.camera.TIS.tisgrabber as tis

from core.module import Base
from interface.camera_interface import CameraInterface


class CallbackUserdata(ctypes.Structure):
    """ User data passed to the callback function and fo take frame.
     """

    def __init__(self):
        self.width = 0
        self.height = 0
        self.BytesPerPixel = 0
        self.buffer_size = 0
        self.color_format = 0
        self.cvMat = None


class UsbCamera(Base, CameraInterface):
    UserData = CallbackUserdata()

    ic = ctypes.cdll.LoadLibrary("D:/qudiFerroLab/hardware/camera/TIS/tisgrabber_x64.dll")
    tis.declareFunctions(ic)
    ic.IC_InitLibrary(0)
    hGrabber = ic.IC_CreateGrabber()

    _camera_name = 'DMK 33UX264'

    _exposure = ctypes.c_long()
    _gain = ctypes.c_long()

    _bpp = None
    _resolution = None
    _data = None
    imagedata = None

    _acquiring = False
    _live = False
    count = 0

    def on_activate(self):
        """ Initialisation performed during activation of the module.
       """
        # self.hGrabber = self.ic.IC_ShowDeviceSelectionDialog(None)  # for fine tuning
        self.ic.IC_OpenVideoCaptureDevice(self.hGrabber, tis.T(self._camera_name))
        self.CreateUserData()
        self.count = 0

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.ic.IC_ReleaseGrabber(self.hGrabber)
        _acquiring = False
        _live = False

    def get_name(self):
        """ Retrieve an identifier of the camera that the GUI can print
        @return string: name for the camera
        """
        return self._camera_name

    def CreateUserData(self):
        ''' Create the user data for callback for the passed camera
        :param ud User data to create
        :param camera The camera connected to the user data
        '''
        self.ic.IC_StartLive(self.hGrabber, 0)
        self.UserData.width = ctypes.c_long()
        self.UserData.height = ctypes.c_long()
        self.UserData.color_format = ctypes.c_int()
        iBitsPerPixel = ctypes.c_int()

        # Query the values
        self.ic.IC_GetImageDescription(self.hGrabber, self.UserData.width, self.UserData.height,
                                       iBitsPerPixel, self.UserData.color_format)

        self.UserData.BytesPerPixel = int(iBitsPerPixel.value / 8.0)
        self.UserData.buffer_size = self.UserData.width.value * self.UserData.height.value * self.UserData.BytesPerPixel
        self.ic.IC_StopLive(self.hGrabber)

    def get_size(self):
        """ Retrieve size of the image in pixel
        @return tuple: Size (width, height)
        """
        # self._width = self.ic.IC_GetVideoFormatWidth(self.hGrabber)
        # self._height = self.ic.IC_GetVideoFormatHeight(self.hGrabber)

        self._resolution = (self.UserData.width, self.UserData.height)

        return self._resolution

    def support_live_acquisition(self):
        """ Return whether the camera can take care of live acquisition
        @return bool: True if supported, False if not
        """
        return True

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
            print("good")

    Callbackfunc = ic.FRAMEREADYCALLBACK(FrameCallback)

    def start_live_acquisition(self):
        """ Start a continuous acquisition
            Set the camera in live mode
                """

        self._acquiring = True
        self._live = True

        self.ic.IC_SetContinuousMode(self.hGrabber, 0)
        self.ic.IC_StartLive(self.hGrabber, 0)

        if self.count < 1:
            self.ic.IC_SetFrameReadyCallback(self.hGrabber, self.Callbackfunc, self.UserData)
            self.count = 1

    def get_frame_data(self):
        """ Return array for live acquisition"""
        return self.UserData.cvMat

    def start_single_acquisition(self):
        """ Start a single acquisition
        """

        self._acquiring = True
        self.take_frame()
        time.sleep(float(1 / 100))
        self._acquiring = False

    def stop_acquisition(self):
        """ Stop/abort live or single acquisition
        """
        self._live = False
        self._acquiring = False
        # self.ic.IC_SetContinuousMode(self.hGrabber, 1)
        self.ic.IC_StopLive(self.hGrabber)

    def take_frame(self):
        """ Acquired single image.
        Each pixel might be a float, integer or sub pixels
        """
        if self.ic.IC_IsDevValid(self.hGrabber):
            self.ic.IC_SetContinuousMode(self.hGrabber, 1)
            self.ic.IC_StartLive(self.hGrabber, 0)

            if self.ic.IC_SnapImage(self.hGrabber, 1000) == tis.IC_SUCCESS:
                # # Get the image data
                imagePtr = self.ic.IC_GetImagePtr(self.hGrabber)
                self.imagedata = ctypes.cast(imagePtr, ctypes.POINTER(ctypes.c_ubyte * self.UserData.buffer_size))
                # # Create the numpy array
                self._data = np.ndarray(buffer=self.imagedata.contents, dtype=np.uint8,
                                        shape=(self.UserData.height.value, self.UserData.width.value,
                                               self.UserData.BytesPerPixel))

            self.ic.IC_StopLive(self.hGrabber)

    def get_acquired_data(self):
        """ Return an array of last acquired image.

        @return numpy array: image data for single shoot in format [[row],[row]...]

        Each pixel might be a float, integer or sub pixels
        """
        return self._data

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
