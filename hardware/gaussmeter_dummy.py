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

# import pyvisa as visa
import time
import numpy as np
# from enum import Enum

from core.module import Base
from core.configoption import ConfigOption

from interface.simple_data_interface import SimpleDataInterface

# class Units(Enum):
#     GAUSS = 1
#     TESLA = 2
#     OERSTED = 3
#     AMPERE_PER_METER = 4


class GaussmeterDummy(Base, SimpleDataInterface):
    """
    Main class for the Model 425 gaussmeter emulation.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        _units = 'TESLA'
        # self._units = Units

    _modclass = 'gaussmeter'
    _modtype = 'hardware'

    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        """
        self.connect()
        self.set_units('TESLA')  # We will always switch to T units in startup
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

        try:
            time.sleep(1)
            self.log.info(f"Gaussmeter {self._gaussmeter_handle.query('*IDN?')} is connected")
        except:
            self.log.warning('Cannot connect to delay line! Check ports!')

    def disconnect(self):
        time.sleep(0.5)

    def set_units(self, unit='TESLA'):
        """
        Sets units, see Enum class for description
        """
        if unit == 'TESLA' or 'OERSTED' or 'GAUSS' or 'AMPERE_PER_METER':
            self._units = unit
        else:
            self.log.warning('Wrong units name, use "TESLA", "OERSTED", "GAUSS", "AMPERE_PER_METER"')

    def get_units(self):
        return self._units

    def getChannels(self):
        pass

    def getData(self):
        """ Returns reading in mT"""
        return np.random.uniform()

    def zero_probe(self):
        """Zeroing probe and wait til it is finished"""
        self.log.info("Starting zeroing the probe, it will take some time.")
        time.sleep(10)


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
