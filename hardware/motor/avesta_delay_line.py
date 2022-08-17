# -*- coding: utf-8 -*-

"""
This file contains the hardware control of delay line controlled
by avesta controller.

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

import visa
import time

from core.module import Base
from core.configoption import ConfigOption

from interface.motor_interface import MotorInterface

# all interactions are use query to remove echo and first symbol stripped to remove /n char

class avestaDelay(Base,MotorInterface):
    """
    Main class for delay line control.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    _modclass = 'fhr1000'
    _modtype = 'hardware'

    _com_port_delayline = ConfigOption('com_port_delayline', 'ASRL4::INSTR', missing='warn')

    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        """

        self.rm = visa.ResourceManager()
        try:
            self._delayline_handle = self.rm.open_resource(self._com_port_delayline,
                                                           baud_rate=57600,
                                                           data_bits=8,
                                                           write_termination='\r',
                                                           read_termination='\r')
        except:
            self.log.warning('Cannot connect to delay line! Check ports.')

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._delayline_handle.close()

    def abort(self):
        self._delayline_handle.query("ms")

    def calibrate(self):
        while self.get_status() == 'S0':
            time.sleep(0.05)
            self.move_rel(-30000)
            time.sleep(1.5)
        while self.get_status() == 'S-':
            time.sleep(0.05)
            self._delayline_handle.query('mrsw')  # special command to move out
            time.sleep(3)
        if self.get_status() == 'S0':             # of the end switch
            time.sleep(0.5)
            self._delayline_handle.query("msp pos 0")  # set absolute position
                                                       # as zero in steps
    def get_constraints(self):
        pass

    def get_pos(self, param_list=None):
        self._delayline_handle.query("mp")
        return int(self._delayline_handle.read()[1:])

    def get_status(self, param_list=None):
        """
        Gets status of the delay line motor.
        S0 - stopped, not in the end switch
        M - moving
        S- or S+ - stopped in the negative or positive end switch
        """
        self._delayline_handle.query("mgs")
        return self._delayline_handle.read()[1:]  # remove first symbol /n

    def get_velocity(self, param_list=None):
        pass

    def move_abs(self, step):
        old_position = self.get_pos()
        self.move_rel(step-old_position)

    def move_rel(self, step):
        if self.get_status() == 'S0':  # S0 is neutral status
            self._delayline_handle.query("mm " + str(step))
        else:
            pass

    def set_velocity(self, param_dict):
        pass
