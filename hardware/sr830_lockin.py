# -*- coding: utf-8 -*-

"""
This file contains the hardware control of the SR830 lock-in amplifier by STANDFORD RESEARCH.
Only RS232 communication is realized with control through SCPI instructions.

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

from interface.simple_data_interface import SimpleDataInterface


# TODO: all interactions are use query to remove echo and first symbol stripped to remove /n char

class sr830LockIn(Base, SimpleDataInterface):
    """
    Main class for lock-in control.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    _modclass = 'sr830'
    _modtype = 'hardware'

    _com_port_lock_in = ConfigOption('com_port_lock_in', 'ASRL5::INSTR', missing='warn')

    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        """

        self.rm = visa.ResourceManager()
        try:
            self._lock_in_handle = self.rm.open_resource(self._com_port_lock_in,
                                                           baud_rate = 19200,
                                                           parity=0,
                                                           write_termination='\r',
                                                           read_termination='\r')
            time.sleep(0.3)
            self.log.info("All good, lock-in is conected")
        except:
            self.log.warning('Cannot connect to lock-in! Check ports.')

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._lock_in_handle.close()

    def getData(self):
        """ Returns X, Y, R, Theta as an array of floats. """
        _data = self._lock_in_handle.query("snap?1,2,3,4")
        return list(map(float, _data.split(',')))

    def getChannels(self):
        pass

    # def abort(self):
    #     self._delayline_handle.query("ms")
    #
    # def calibrate(self):
    #     while self.get_status() == 'S0':
    #         time.sleep(0.05)
    #         self.move_rel(-30000)
    #         time.sleep(1.5)
    #     while self.get_status() == 'S-':
    #         time.sleep(0.05)
    #         self._delayline_handle.query('mrsw')  # special command to move out
    #         time.sleep(3)
    #     if self.get_status() == 'S0':  # of the end switch
    #         time.sleep(0.5)
    #         self._delayline_handle.query("msp pos 0")  # set absolute position
    #         # as zero in steps
    #
    # def get_constraints(self):
    #     pass
    #
    # def get_pos(self, param_list=None):
    #     self._delayline_handle.query("mp")
    #     return int(self._delayline_handle.read()[1:])
    #
    # def get_status(self, param_list=None):
    #     """
    #     Gets status of the delay line motor.
    #     S0 - stopped, not in the end switch
    #     M - moving
    #     S- or S+ - stopped in the negative or positive end switch
    #     """
    #     self._delayline_handle.query("mgs")
    #     return self._delayline_handle.read()[1:]  # remove first symbol /n
    #
    # def get_velocity(self, param_list=None):
    #     pass
    #
    # def move_abs(self, step):
    #     old_position = self.get_pos()
    #     self.move_rel(step - old_position)
    #
    # def move_rel(self, step):
    #     if self.get_status() == 'S0':  # S0 is neutral status
    #         self._delayline_handle.query("mm " + str(step))
    #     else:
    #         pass
    #
    # def set_velocity(self, param_dict):
    #     pass
