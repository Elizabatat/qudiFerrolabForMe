# -*- coding: utf-8 -*-

"""
A module for controlling a camera.

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

from core.module import Connector
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic
from qtpy import QtCore
import matplotlib.pyplot as plt

import datetime
from collections import OrderedDict
import time


class CameraLogic(GenericLogic):
    """
    Control a camera.
    """

    # declare connectors
    hardware = Connector(interface='CameraInterface')
    savelogic = Connector(interface='SaveLogic')
    hv = Connector(interface='HighVoltageLogic')

    _max_fps = 35.
    _fps = _max_fps
    _wait_time = 0.1
    _average = 1

    # signals
    sigUpdateDisplay = QtCore.Signal()
    sigUpdateImageDisplay = QtCore.Signal()
    sigUpdateMeasureDisplay = QtCore.Signal()
    sigMeasureFinished = QtCore.Signal()
    sigAcquisitionFinished = QtCore.Signal()
    sigVideoFinished = QtCore.Signal()

    timer = None
    free = False
    enabled = False
    volt_free = False

    _exposure = 0.1
    _gain = 1.
    _last_image = None
    _last_av_image = np.zeros([2048, 2448, 3])
    _diff_av_image = None

    _step_volt = 1
    _start_volt = 10
    _stop_volt = 10
    _minV = 10 #None
    _maxV = 1000 #None

    voltM = True

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._hardware = self.hardware()
        self._save_logic = self.savelogic()
        self._HV = self.hv()

        self.enabled = False

        self.get_exposure()
        self.get_gain()

        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        #self.timer.timeout.connect(self.loop)

    def on_deactivate(self):
        """ Perform required deactivation. """
        pass

    def set_exposure(self, t):
        """ Set exposure of hardware """

        self._hardware.set_exposure(t)
        self.get_exposure()

    def get_exposure(self):
        """ Get exposure of hardware """

        self._exposure = self._hardware.get_exposure()
        self._fps = abs(max(1 / self._exposure, self._max_fps))
        return self._exposure

    def set_gain(self, gain):
        """ Set gain to hardware """

        self._hardware.set_gain(gain)

    def get_gain(self):
        """ Get exposure of hardware """

        gain = self._hardware.get_gain()
        self._gain = gain
        return gain

    def start_single_acquistion(self):
        """ Take frame and update _last_image and start update display in gui """

        self._hardware.start_single_acquisition()
        self._last_image = self._hardware.get_acquired_data()
        self.sigUpdateImageDisplay.emit()
        self.sigAcquisitionFinished.emit()

    def continuous_get_data(self):
        """ Take frame for video """

        self._last_image = self._hardware.get_frame_data()
        return self._last_image

    def start_loop(self):
        """ Start the data recording loop."""

        self.enabled = True
        self.free = True

        self.timer.start(1000)

        if self._hardware.support_live_acquisition():
            self._hardware.start_live_acquisition()
            self.sigUpdateDisplay.emit()

    def measure_start_loop(self, v=0):
        """ Start averaging and subtracting loop."""
        timestamp = datetime.datetime.now()
        print("start" , timestamp )
        ch = np.zeros([self._hardware.UserData.height.value, self._hardware.UserData.width.value,
                              self._hardware.UserData.BytesPerPixel])
        # self._last_av_image = np.zeros([self._hardware._height.value, self._hardware._width.value, self._hardware._bpp])
        _av_image = np.zeros([self._hardware.UserData.height.value, self._hardware.UserData.width.value,
                              self._hardware.UserData.BytesPerPixel])
        # _av_image = self._last_image
        N = np.zeros([self._average, self._hardware.UserData.height.value,
                      self._hardware.UserData.width.value, self._hardware.UserData.BytesPerPixel])

        #for i in range(self._average):
            # self._hardware.start_single_acquisition()
            # image = self._hardware.get_acquired_data()
            # N[i] = image
            #
        for i in range(self._average):
            self._hardware.start_single_acquisition()
            # time.sleep(self._wait_time)
            image = self._hardware.get_acquired_data()
            while image.all() == ch.all():
                self._hardware.start_single_acquisition()
                # time.sleep(self._wait_time)
                image = self._hardware.get_acquired_data()

            N[i] = image


        """ averaging  """
        #_av_image = self.rgb2gray(np.mean(N, axis=0))
        _av_image = np.mean(N, axis=0)

        """ difference  """
        diff_av_image = _av_image - self._last_av_image

        self._diff_av_image = diff_av_image
        self.save_xy_data(self.rgb2gray(self._diff_av_image), "diff", self._average,v)

        self._last_av_image = _av_image
        self.save_xy_data(self.rgb2gray(self._last_av_image), "av", self._average,v)

        self.sigUpdateMeasureDisplay.emit()
        self.sigAcquisitionFinished.emit()

    def start_voltage_measurements(self):
        """Start loop for measurement with voltage and averaging """

        self.enabled = True

        for i in range(self._start_volt, self._stop_volt, self._step_volt):
            if self.volt_free:
                self._HV.do_loop(i)
                #self.measure_start_loop(i)
                time.sleep(10)


        print("end")

        self.sigMeasureFinished.emit()


    def stop_voltage_measurements(self):
        """Stop/abort loop for measurement with voltage and averaging """

        self.enabled = False
        self.volt_free = False
        print("stop")
        self.sigMeasureFinished.emit()

    @QtCore.Slot()
    def stop_loop(self):
        """ Stop the data recording loop. """

        self.timer.stop()
        self.free = False
        self.enabled = False


        self._hardware.stop_acquisition()
        self.sigVideoFinished.emit()

    def loop(self):
        """ Execute step in the data recording loop: save one of each control and process values """

        self._last_image = self._hardware.get_acquired_data()
        self.sigUpdateDisplay.emit()
        if self.enabled:
            self.timer.start(1000)
            # if not self._hardware.support_live_acquisition():
            self._hardware.start_single_acquisition()  # the hardware has to check it's not busy

    def get_last_image(self):
        """ Return last acquired image """

        self._last_image = self._hardware.get_acquired_data()
        return self._last_image

    def get_diff_av_image(self):
        """ Return last acquired image """
        return self._diff_av_image

    def save_xy_data(self, imdata, name, av, volt=None, filename=None):
        """ Save the current confocal xy data to file.

        Two files are created.  The first is the imagedata, which has a text-matrix of count values
        corresponding to the pixel matrix of the image.  Only count-values are saved here.

        """
        filepath = self._save_logic.get_path_for_module('Camera')
        timestamp = datetime.datetime.now()
        # Prepare the metadata parameters (common to both saved files):
        parameters = OrderedDict()

        parameters['Gain'] = self._gain
        parameters['Exposure time (s)'] = self._exposure

        # Prepare a figure to be saved

        fig = self.draw_figure(data=imdata)

        # data for the text-array "image":
        image_data = OrderedDict()
        image_data['XY image data.'] = imdata  # self._last_image
        if filename == None:
            filename = 'xy_image' + str(name)

        filelabel = filename + '_av=' + str(av) + '_voltage=' + str(volt)

        self._save_logic.save_data(image_data,
                                   filepath=filepath,
                                   timestamp=timestamp,
                                   parameters=parameters,
                                   filelabel=filelabel,
                                   fmt='%.6e',
                                   delimiter='\t',
                                   plotfig=fig)

        self.log.debug('Image saved.')
        print(timestamp)
        return

    def draw_figure(self, data):
        """ Create a 2-D color map figure of the scan image.

        """

        # Scale color values using SI prefix
        image_data = data

        # Use qudi style
        plt.style.use(self._save_logic.mpl_qd_style)

        # Create figure
        fig, ax = plt.subplots()

        # Create image plot
        cfimage = ax.imshow(image_data,
                            cmap=plt.get_cmap('inferno'),  # reference the right place in qd
                            origin="lower", interpolation='none')
        ax.axis('off')

        return fig

    def rgb2gray(self, rgb):
        """ Convert rgb to gray """
        r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        gray = 0.2989 * r + 0.5870 * g + 0.1140 * b

        return gray
