# -*- coding: utf-8 -*-

"""
This file contains the hardware control of the delay line
(in principle any motor, but tested only with brushless delay line LTS300/M
controlled by integrated controller) via .NET communication protocol/software Kinesis.

It is necessary to have Kinesis installed (maybe only .dlls, not yet tested)
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
clr.AddReference("Thorlabs.MotionControl.IntegratedStepperMotorsCLI")
clr.AddReference("Thorlabs.MotionControl.Controls")
import Thorlabs.MotionControl.Controls
from Thorlabs.MotionControl.DeviceManagerCLI import *
from Thorlabs.MotionControl.IntegratedStepperMotorsCLI import *

from core.module import Base
from core.configoption import ConfigOption

from interface.motor_interface import MotorInterface

# the communication is done via thorlabs DLLs withe the use od the .NET


class thorlabsDelay(Base, MotorInterface):
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


    def connect(self):
        """In contrast to brushless delay line here is no external controller,
           so we can connect directly to delay line avoiding
           controller_handel and channel selection procedures
        """
        # TODO: better check necessary delays for conections
        DeviceManagerCLI.CheckForConnectionChanges()
        DeviceManagerCLI.GetDeviceList()
        self._device_handle = LongTravelStage.CreateLongTravelStage(str(self._serial_number_controller))
        self._device_handle.Connect(str(self._serial_number_controller))
        self._device_handle.WaitForSettingsInitialized(5000)
        self._device_handle.StartPolling(250)
        time.sleep(0.5)
        self._device_handle.EnableDevice()
        time.sleep(0.5)
        self._device_handle.LoadMotorConfiguration(self._device_handle.get_DeviceID())

        if self._device_handle.IsConnected and self._device_handle.IsEnabled \
                and self._device_handle.IsSettingsKnown and self._device_handle.IsMotorSettingsValid \
                and self._device_handle.IsSettingsInitialized():
            self.log.info("All good, controller and device are ready to go!")
        else:
            self.log.warning("Problems with the connection to the delay line. Check all connections and serial number.")

    def disconnect(self):
        self._device_handle.StopPolling()
        self._device_handle.DisableDevice()
        self._device_handle.Disconnect()

    @property
    def is_running(self):
        """
        Read-only flag for checking if delay line is busy
        """
        # return self._is_running
        return self._device_handle.IsDeviceBusy

    def abort(self):
        pass

    def calibrate(self):
        pass

    def get_constraints(self):
        """Get position constrains (in a real units, in our case mm) from the device.
            Returns a list of the constrains"""
        self._min_pos = float(str(self._device_handle.get_MotorDeviceSettings().get_Physical().MinPosUnit))
        self._max_pos = float(str(self._device_handle.get_MotorDeviceSettings().get_Physical().MaxPosUnit))
        return [self._min_pos, self._max_pos]

    def get_status(self, param_list=None):
        pass

    def get_velocity(self, param_list=None):
        return float(str(self._device_handle.GetVelocityParams().MaxVelocity))

    def get_acceleration(self, param_list=None):
        return float(str(self._device_handle.GetVelocityParams().Acceleration))

    def get_pos(self):
        return float(str(self._device_handle.get_Position()))

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
                self._device_handle.MoveTo(Decimal(position_mm), 60000)
                self.wait_until_done()
                time.sleep(0.05)
            else:
                break
        return 0

    def move_rel(self, rel_position_mm):
        if self.is_running:
            self.log.warning('Unable to move. Already moving.')
            return 0

        self.move_abs(self.get_pos() + rel_position_mm)
        return 0

    def stop_movements(self):
        if self.is_running:
            self._is_running = False
        return 0

    def set_velocity(self, param_dict):
        pass

    def wait_until_done(self):
        while self._device_handle.IsDeviceBusy:
            time.sleep(0.05)

    def home(self):
        pass
        """ Home delay line within 60s by moving it forward and back to zero"""
        self._device_handle.Home(60000)
