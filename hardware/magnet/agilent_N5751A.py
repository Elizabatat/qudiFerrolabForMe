# -*- coding: utf-8 -*-
"""

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


class N5751AgilentPowerSource(Base, ProcessControlInterface):
    """ Hardware module for power supply Agilent N5751 to for magnet control.

    Example config :
        voltage_generator:
            module.Class: 'power_supply.Keysight_E3631A.E3631A'
            address: 'ASRL9::INSTR'

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    _modclass = 'powersource'
    _modtype = 'hardware'

    _com_port_powersource = ConfigOption('com_port_powersource', missing='error')

    # _voltage_min = ConfigOption('voltage_min', 0)
    # _voltage_max = ConfigOption('voltage_max', 6)
    # _current_max = ConfigOption('current_max', missing='error')

    def on_activate(self):
        """We will assume that we will always work in constant current mode,
        thus output voltage would be put to maximum (300 V) at start"""
        self.connect()
        self._powersource_handle.query("VOLT 300; *OPC?")

    def on_deactivate(self):
        self.disconnect()

    def connect(self):
        """Connect power source
        """

        self.rm = visa.ResourceManager()  # when there is no argument - Keysight IVI backend is used
        try:
            self._powersource_handle = self.rm.open_resource(self._com_port_powersource,
                                                             read_termination='\n'
                                                             )
            self.log.info(f"Powersource {self._powersource_handle.query('*IDN?')} is connected")
        except:
            self.log.warning('Cannot connect to powersource! Check ports and power on the device!')

    def disconnect(self):
        self.output_off()
        self._powersource_handle.close()

    def output_on(self):
        """Turn on output"""
        self._powersource_handle.query('OUTP ON; *OPC?')

    def output_off(self):
        """Turn off output
        in the
        """
        self._powersource_handle.query('OUTP OFF; *OPC?')

    def get_voltage_v(self):
        return float(self._powersource_handle.query('VOLT?'))

    def set_voltage_v(self, voltage_v=0):
        self._powersource_handle.query(f'VOLT {voltage_v}; *OPC?')

    def get_current_a(self):
        return float(self._powersource_handle.query('CURR?'))

    def set_current_a(self, current_a=0):
        self._powersource_handle.query(f'CURR {current_a}; *OPC?')

    def _write(self, cmd):
        """ Function to write command to hardware"""
        # self._inst.write(cmd)
        # time.sleep(.01)
        pass

    def _query(self, cmd):
        """ Function to query hardware"""
        # return self._inst.query(cmd)

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