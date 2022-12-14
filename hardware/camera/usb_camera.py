# -*- coding: utf-8 -*-

"""
Cheap aliexpress hayear camera connected via usb interface.
Camera name ELP-USBGS720P02-SFV(5-50)

This camera has a weird autoexposure settings:
usb_elp_camera._camera_handle.set(cv2.CAP_PROP_AUTO_EXPOSURE,0.75) - ON
usb_elp_camera._camera_handle.set(cv2.CAP_PROP_AUTO_EXPOSURE,0.75) - OFF

Exposure ones:
usb_elp_camera._camera_handle.set(cv2.CAP_PROP_EXPOSURE,-1) seems it accept values from -13 to 0

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

import numpy as np
import time
import cv2
from core.module import Base
from core.configoption import ConfigOption
from interface.camera_interface import CameraInterface


class UsbCamera(Base, CameraInterface):
    """ Dummy hardware for camera interface

    Example config for copy-paste:

    camera_dummy:
        module.Class: 'camera.camera_dummy.CameraDummy'
        support_live: True
        camera_name: 'Dummy camera'
        resolution: (1280, 720)
        exposure: 0.1
        gain: 1.0
    """

    _support_live = ConfigOption('support_live', True)
    _camera_name = ConfigOption('camera_name', 'Dummy camera')
    _resolution = ConfigOption('resolution', (1280, 720))  # High-definition !

    _live = False
    _acquiring = False
    _exposure = ConfigOption('exposure', .1)
    _gain = ConfigOption('gain', 1.)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._camera_handle = cv2.VideoCapture(0)
        self._resolution = (self._camera_handle.get(cv2.CAP_PROP_FRAME_WIDTH), self._camera_handle.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._resolution = tuple(map(int, self._resolution))  # convert resolution to integers

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._camera_handle.release()
        self.stop_acquisition()

    def get_name(self):
        """ Retrieve an identifier of the camera that the GUI can print

        @return string: name for the camera
        """
        # return self._camera_name
        pass

    def get_size(self):
        """ Retrieve size of the image in pixel

        @return tuple: Size (width, height)
        """
        return self._resolution

    def support_live_acquisition(self):
        """ Return whether or not the camera can take care of live acquisition

        @return bool: True if supported, False if not
        """
        return self._support_live

    def start_live_acquisition(self):
        """ Start a continuous acquisition

        @return bool: Success ?
        """
        if self._support_live:
            self._live = True
            self._acquiring = False

    def start_single_acquisition(self):
        """ Start a single acquisition

        @return bool: Success ?
        """
        if self._live:
            return False
        else:
            self._acquiring = True
            time.sleep(float(100/1000))
            self._acquiring = False
            return True

    def stop_acquisition(self):
        """ Stop/abort live or single acquisition

        @return bool: Success ?
        """
        self._live = False
        self._acquiring = False

    def get_acquired_data(self):
        """ Return an array of last acquired image.

        @return numpy array: image data in format [[row],[row]...]

        Each pixel might be a float, integer or sub pixels
        """
        _, data = self._camera_handle.read()

        return data[:,:,:] # since this is BW camera we will use only one channel

    def set_exposure(self, exposure):
        """ Set the exposure time in seconds

        @param float time: desired new exposure time

        @return float: setted new exposure time
        """
        self._exposure = exposure  # baka!
        self._camera_handle.set(cv2.CAP_PROP_EXPOSURE, exposure)

    def get_exposure(self):
        """ Get the exposure time in seconds

        @return float exposure time
        """
        return self._camera_handle.get(cv2.CAP_PROP_EXPOSURE)

    def set_gain(self, gain):
        """ Set the gain

        @param float gain: desired new gain

        @return float: new exposure gain
        """
        self._gain = gain
        return self._gain

    def get_gain(self):
        """ Get the gain

        @return float: exposure gain
        """
        return self._gain

    def get_ready_state(self):
        """ Is the camera ready for an acquisition ?

        @return bool: ready ?
        """
        return not (self._live or self._acquiring)


