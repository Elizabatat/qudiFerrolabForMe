# -*- coding: utf-8 -*-

"""
This file contains the hardware control of the delay line
(in principle any motor, but tested only with stepper delay line M-IMS600PP
controlled by ESP 301 controller) via usual usb communication.

It was necessary to install controller usb drivers obtained from https://www.newport.com/p/ESP301-3N
(you have to install ESP301_Installer_Win10 and install driver from ESP301/Bin/USB Driver/ directory)

Everywhere below we assume that controller controls single axis, thus all commands should be prepended
with 1, eg. '1 ID ?'

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

import visa
import time

from core.module import Base
from core.configoption import ConfigOption

from interface.motor_interface import MotorInterface


class newportDelay(Base, MotorInterface):
    """
    Main class for the DDS600 delay line control.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._is_running = False

    _modclass = 'delay_line'
    _modtype = 'hardware'

    _com_port_delay_line = ConfigOption('com_port_delay_line', 'ASRL4::INSTR', missing='warn')

    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        """
        self.connect()

        # set returned 'resolution' of the position to 4 digits after point
        time.sleep(0.1)
        self._delay_line_handle.write('1FP4')

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

        self.rm = visa.ResourceManager()
        try:
            self._delay_line_handle = self.rm.open_resource(self._com_port_delay_line,
                                                            baud_rate=921600,
                                                            parity=0,  # None
                                                            data_bits=8,
                                                            stop_bits=10,  # one
                                                            write_termination='\r',
                                                            read_termination='\r'
                                                            )
            time.sleep(0.1)
            self.log.info(f" Delay line {self._delay_line_handle.query('1 ID ?')} is connected")
        except:
            self.log.warning('Cannot connect to delay line! Check ports!')

    def disconnect(self):
        self._delay_line_handle.close()

    @property
    def is_running(self):
        """
        Read-only flag for checking if delay line is busy
        """
        return not int(str.strip(self._delay_line_handle.query('1 MD ?'), '/n/r '))

    def abort(self):
        pass

    def calibrate(self):
        pass

    def get_constraints(self):
        """Get position constrains (in a real units, in our case mm) from the device.
            Returns a list of the constrains"""
        self._min_pos = float(str.strip(self._delay_line_handle.query('1 SL ?'), '/n/r '))
        self._max_pos = float(str.strip(self._delay_line_handle.query('1 SR ?'), '/n/r '))
        return [self._min_pos, self._max_pos]

    def get_status(self, param_list=None):
        pass

    def get_velocity(self, param_list=None):
        return float(str.strip(self._delay_line_handle.query('1 VA ?'), '/n/r '))

    def set_velocity(self, param_dict):
        pass

    def get_acceleration(self, param_list=None):
        return float(str.strip(self._delay_line_handle.query('1 AC ?'), '/n/r '))

    def get_pos(self):
        return float(str.strip(self._delay_line_handle.query('1 TP ?'), '/n/r '))

    def move_abs(self, position_mm):
        if self.is_running:
            self.log.warning('Unable to move. Already moving.')
            return -1

        self._is_running = True

        self._delay_line_handle.write(f'1 PA {position_mm}')
        self.wait_until_done()
        time.sleep(0.1)  # this additional delay in necessary to precise position reading due to retroreflector inertia

        # Not sure if this is necessary for this delay line!
        # for i in range(10):
        #     if self.get_pos() != position_mm:
        #         self._device_handle.MoveTo(Decimal(position_mm), 60000)
        #         self.wait_until_done()
        #         time.sleep(0.05)
        #     else:
        #         break
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

    def wait_until_done(self):
        while self.is_running:
            time.sleep(0.05)

    def home(self):
        """ Home delay line by moving it to predefined position"""
        self._delay_line_handle.query('1 OR')
