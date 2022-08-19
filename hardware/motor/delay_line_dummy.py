# -*- coding: utf-8 -*-

"""
This file contains delay line hardware dummy for delay line emulation.

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

import time

from core.module import Base
from core.configoption import ConfigOption

from interface.motor_interface import MotorInterface


class DelayLineDummy(Base, MotorInterface):
    """
    Main class for the generic delay line dummy.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._is_running = False
        self._position = 0.0  # TODO: status var? Since we cannot read

    _modclass = 'delay_line'
    _modtype = 'hardware'

    _delay_line_constrains = ConfigOption('constrains', [0.0, 600.0], missing='warn')

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
        return self._is_running

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
        """Declared in the configuration file."""
        return self._delay_line_constrains

    def get_status(self, param_list=None):
        pass

    def get_velocity(self, param_list=None):
        pass

    def get_pos(self):
        return self._position

    def move_abs(self, position_mm):
        if self.is_running:
            self.log.warning('Unable to move. Already moving.')
            return -1

        self._is_running = True
        self.wait(abs((self.get_pos()-position_mm)*0.1))
        self._position = position_mm
        self._is_running = False

    def move_rel(self, rel_position_mm):
        self._position = self._position + rel_position_mm

    def stop_movements(self):
        if self.is_running:
            self._is_running = False
        return 0

    def set_velocity(self, param_dict):
        pass

    def connect(self):
        time.sleep(1)
        self.log.info("All good, controller and device are ready to go!")

    def disconnect(self):
        time.sleep(0.5)

    def wait_until_done(self):
        while self._is_running:
            time.sleep(0.05)

    def wait(self, wait_s):
        time.sleep(wait_s)

    def home(self):
        """ Home delay line within 60s by moving it forward and back to zero"""
        time.sleep(10)
        self._position = 0


