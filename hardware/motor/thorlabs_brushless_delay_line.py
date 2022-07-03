# -*- coding: utf-8 -*-

"""
This file contains the hardware control of the delay line
(in principle any motor, but tested only with brushless delay line DDS600/M controlled by BBD201)
controlled by the Thorlabs controller via .NET communication protocol/software Kinesis.

It is necessary to have Kinesis installed (maybe only .dlls, not tested)
obtainable from https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=Motion_Control&viewtab=0

qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import clr
import sys
import time

from System import String
from System import Decimal
from System.Collections import *

# The weird import is due to the fact that we have to import Kinesis first
# and it was kinda impossible to import also, kinesis path is hardcoded
# TODO: make kinesis import better somehow!

sys.path.append(r'C:\Program Files\Thorlabs\Kinesis')
clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
clr.AddReference("Thorlabs.MotionControl.Benchtop.BrushlessMotorCLI")
clr.AddReference("Thorlabs.MotionControl.Controls")
import Thorlabs.MotionControl.Controls
from Thorlabs.MotionControl.DeviceManagerCLI import *
from Thorlabs.MotionControl.Benchtop.BrushlessMotorCLI import *

from core.module import Base
from core.configoption import ConfigOption

from interface.motor_interface import MotorInterface

# the communication is done via thorlabs DLLs withe the use od the .NET

class thorlabsDelay(Base,MotorInterface):
    """
    Main class for the DDS600 delay line control.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._is_running = False

    _modclass = 'delay_line'
    _modtype = 'hardware'

    # it is possible to scan it automatically but it is done manually to consider the case of a few controllers
    _serial_number_controller = ConfigOption('serial_number_controller', '73139754', missing='warn')
    _kinesis_path = ConfigOption('kinesis_path', r'C:\Program Files\Thorlabs\Kinesis', missing='warn')

    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        """
        self.connect()

        self._is_running = False

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.disconnect()

        self._is_running = False

    @property
    def is_running(self):
        """
        Read-only flag for checking if delay line is busy
        """
        # return self._is_running
        return self._channel_handle.IsDeviceBusy

    def abort(self):
        pass
        # self._delayline_handle.query("ms")

    def calibrate(self):
        pass
        # while self.get_status() == 'S0':
        #     time.sleep(0.05)
        #     self.move_rel(-30000)
        #     time.sleep(1.5)
        # while self.get_status() == 'S-':
        #     time.sleep(0.05)
        #     self._delayline_handle.query('mrsw')  # special command to move out
        #     time.sleep(3)
        # if self.get_status() == 'S0':             # of the end switch
        #     time.sleep(0.5)
        #     self._delayline_handle.query("msp pos 0")  # set absolute position
        #                                                # as zero in steps

    def get_constraints(self):
        """Get position constrains (in a real units, in our case mm) from the device.
            Returns a list of the constrains"""
        self._min_pos = float(str(self._channel_handle.get_MotorDeviceSettings().get_Physical().MinPosUnit))
        self._max_pos = float(str(self._channel_handle.get_MotorDeviceSettings().get_Physical().MaxPosUnit))
        return [self._min_pos, self._max_pos]

    def get_status(self, param_list=None):
        pass

    def get_velocity(self, param_list=None):
        pass

    def get_pos(self):
        return float(str(self._channel_handle.get_Position()))

    def move_abs(self, position_mm):
        if self.is_running:
            self.log.warning('Unable to move. Already moving.')
            return -1

        self._is_running = True

        # This is the dirty hack to move a very small distance ~1 um
        # One movement is typically not enough to reach precice position
        # Thus we wait a bit and move again TODO: dirty hack

        for i in range(10):
            if self.get_pos() != position_mm:
                self._channel_handle.MoveTo(Decimal(position_mm), 60000)
                self.wait_until_done()
                time.sleep(0.05)
            else:
                break
        return 0

    def move_rel(self, rel_position_mm):
        if self.is_running:
            self.log.warning('Unable to move. Already moving.')
            return 0

        self._is_running = True
        self.move_abs(self.get_pos() + rel_position_mm)
        return 0

    def stop_movements(self):
        if self.is_running:
            self._is_running = False
        return 0

    def set_velocity(self, param_dict):
        pass

    def connect(self):
        # TODO: better check necessary delays for conections
        DeviceManagerCLI.CheckForConnectionChanges()
        DeviceManagerCLI.GetDeviceList()
        self._controller_handle = Thorlabs.MotionControl.Benchtop.BrushlessMotorCLI \
            .BenchtopBrushlessMotor.CreateBenchtopBrushlessMotor(str(self._serial_number_controller))
        time.sleep(2)
        self._controller_handle.Connect(str(self._serial_number_controller))
        self._channel_handle = self._controller_handle.GetChannel(1)
        time.sleep(1)  # needed to wait a bit to connect to channel
        self._channel_handle.LoadMotorConfiguration(self._channel_handle.get_DeviceID())
        # time.sleep(1)  # needed to wait a bit to connect to channel
        self._channel_handle.StartPolling(250)
        # time.sleep(1)  # needed to wait a bit to connect to channel
        self._channel_handle.EnableDevice()
        time.sleep(1)  # needed to wait a bit for the enabling of the device and application of settings
        if self._controller_handle.IsConnected and self._channel_handle.IsConnected and self._channel_handle.IsEnabled \
                and self._channel_handle.IsSettingsKnown and self._channel_handle.IsMotorSettingsValid \
                and self._channel_handle.IsSettingsInitialized():
            self.log.info("All good, controller and device are ready to go!")
        else:
            self.log.warning("Problems with the connection to the delay line. Check all connections and serial number.")

    def disconnect(self):
        self._channel_handle.StopPolling()
        self._channel_handle.DisableDevice()
        self._channel_handle.Disconnect()
        self._controller_handle.Disconnect()

    def wait_until_done(self):
        while self._channel_handle.IsDeviceBusy:
            time.sleep(0.05)

    def wait(self, wait_s):
        time.sleep(wait_s)

    def home(self):
        """ Home delay line within 60s by moving it forward and back to zero"""
        self._channel_handle.Home(60000)


