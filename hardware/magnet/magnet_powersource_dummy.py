# -*- coding: utf-8 -*-
"""
This is a dummy file for magnet a powersource. It emulates most of methods with some sleeps highjecked here and there.

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
import time
import pyvisa as visa

from core.module import Base
from core.configoption import ConfigOption
from interface.process_control_interface import ProcessControlInterface


class MagnetPowersourceDummy(Base, ProcessControlInterface):
    """ Dummy for hardware module for power supply Agilent N5751 (and prob others) for magnet control.

    Example config :
        powersource_dummy:
            module.Class: 'magnet.magnet_powersource_dymmy.MagnetPowersourceDummy'
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    _modclass = 'powersource'
    _modtype = 'dummy'

    _voltage = 0.0
    _current = 0.0

    def on_activate(self):
        """We will assume that we will always work in constant current mode,
        thus output voltage would be put to maximum (300 V) at start"""
        self.connect()

    def on_deactivate(self):
        self.disconnect()

    def connect(self):
        """Connect power source
        """
        time.sleep(1)

    def disconnect(self):
        time.sleep(0.5)

    def output_on(self):
        """Turn on output"""
        time.sleep(0.2)

    def output_off(self):
        """Turn off output
        """
        time.sleep(0.2)

    def get_voltage_v(self):
        time.sleep(0.2)
        return self._current

    def set_voltage_v(self, voltage_v=0):
        self._voltage = voltage_v

    def get_current_a(self):
        time.sleep(0.2)
        return self._current

    def set_current_a(self, current_a=0):
        time.sleep(0.01 * current_a)
        self._current = current_a

    def _write(self, cmd):
        """ Function to write command to hardware"""
        # self._inst.write(cmd)
        # time.sleep(.01)
        pass

    def _query(self, cmd):
        """ Function to query hardware"""
        # return self._inst.query(cmd)
        pass

    def set_control_value(self, value):
        """ Set control value, here heating power.

            @param flaot value: control value
        """
        # mini, maxi = self.get_control_limit()
        # if mini <= value <= maxi:
        #     self._write("VOLT {}".format(value))
        # else:
        #     self.log.error('Voltage value {} out of range'.format(value))
        pass

    def get_control_value(self):
        """ Get current control value, here heating power

            @return float: current control value
        """
        # return float(self._query("VOLT?").split('\r')[0])
        pass

    def get_control_unit(self):
        """ Get unit of control value.

            @return tuple(str): short and text unit of control value
        """
        # return 'V', 'Volt'
        pass

    def get_control_limit(self):
        """ Get minimum and maximum of control value.

            @return tuple(float, float): minimum and maximum of control value
        """
        # return self._voltage_min, self._voltage_max
        pass
