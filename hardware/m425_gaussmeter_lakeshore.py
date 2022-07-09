# -*- coding: utf-8 -*-

"""
This file contains the hardware control the Lakeshore Model 425 Gaussmeter

You have to install drivers () from the Lakeshore website to communicate with it via USB

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
from enum import Enum

from core.module import Base
from core.configoption import ConfigOption

from interface.simple_data_interface import SimpleDataInterface


class Units(Enum):
    GAUSS = 1
    TESLA = 2
    OERSTED = 3
    AMPERE_PER_METER = 4


class GaussmeterLakeshore(Base, SimpleDataInterface):
    """
    Main class for the Model 425 gaussmeter control.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        _units = 'TESLA'
        self._units = Units

    _modclass = 'gaussmeter'
    _modtype = 'hardware'

    _com_port_gaussmeter = ConfigOption('com_port_gaussmeter', 'ASRL4::INSTR', missing='warn')

    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        """
        self.connect()
        self.set_units('TESLA')  # We will always switch to T units in startup
        time.sleep(0.05)
        self._gaussmeter_handle.write('RANGE 4')  # Switch to largest range of -3.5 T to 3.5 T
        time.sleep(0.05)
        self._gaussmeter_handle.write('RDGMODE 1,1,2')  # DC, moving average filter is on, narrow band
        time.sleep(0.05)

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.disconnect()

    def connect(self):
        """In contrast to brushless delay line here is no external controller,
           so we can connect directly to delay line avoiding
           controller_handel and channel selection procedures
        """

        self.rm = visa.ResourceManager()
        try:
            self._gaussmeter_handle = self.rm.open_resource(self._com_port_gaussmeter,
                                                            baud_rate=57600,
                                                            parity=1,  # Odd
                                                            data_bits=7,
                                                            stop_bits=10,  # one
                                                            write_termination='\n',
                                                            read_termination='\r\n'
                                                            )
            self.log.info(f"Gaussmeter {self._gaussmeter_handle.query('*IDN?')} is connected")
        except:
            self.log.warning('Cannot connect to delay line! Check ports!')

    def disconnect(self):
        self._gaussmeter_handle.close()

    def set_units(self, unit='TESLA'):
        """
        Sets units, see Enum class for description
        """
        try:
            self._gaussmeter_handle.write(f'UNIT {self._units[unit].value}')
        except:
            self.log.warning('Wrong units name, use "TESLA", "OERSTED", "GAUSS", "AMPERE_PER_METER"')

    def get_units(self):
        val = int(self._gaussmeter_handle.query('UNIT?'))
        return self._units(val).name

    def getChannels(self):
        pass

    def getData(self):
        """ Returns reading in mT"""
        return float(self._gaussmeter_handle.query('RDGFIELD?'))

    def zero_probe(self):
        """Zeroing probe and wait til it is finished"""
        self._gaussmeter_handle.write(f'ZPROBE')
        while int(self._gaussmeter_handle.query('OPST?')) != 132:  # 132 is the code of finishing zeroing probe
            time.sleep(0.05)

    # @property
    # def is_busy(self):
    #     """
    #     Read-only flag for checking if gaussmeter is busy
    #     """
    #     if int(self._gaussmeter_handle.query('OPST?')) != 132:
    #         return True
    #     else:
    #         return False

    def wait(self, s=0.1):
        time.sleep(s)
