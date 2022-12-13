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
import pyvisa

from core.module import Base
from core.configoption import ConfigOption
from interface.process_control_interface import ProcessControlInterface


class PowerSupply(Base, ProcessControlInterface):
    """ Hardware module for power supply Voltcraft PPS11815.

        Example config :
            voltage_generator:
                module.Class: 'power_supply.VoltCraft_PPS_test.PowerSupply'
                address: 'ASRL9::INSTR'
                current_max: 5.
                voltage_max: 60.

        """
    _address = ConfigOption('address', missing='error')

    _current_max = 0.6
    _voltage_max = 10.
    _voltage_min = 1

    _inst = None
    model = ''
    is_open = False
    ready = False

    def on_activate(self):
        """ Startup the module """

        rm = pyvisa.ResourceManager()

        try:
            self._inst = rm.open_resource(self._address,
                                          baud_rate=9600,
                                          parity=0,
                                          stop_bits=10,
                                          data_bits=8,
                                          write_termination='\r',
                                          read_termination=''
                                          )
            self.is_open = True
            self.log.info('Successful open device')
        except pyvisa.VisaIOError:
            self.log.error('Could not connect to hardware. Please check the wires and the address.')

        self.model = "PPS11815"
        self.out_on()
        self.write_voltage(self._voltage_max)

    def on_deactivate(self):
        """ Stops the module """
        self.reset_value()
        self.out_off()
        self.is_open = False
        self._inst.close()
        self.log.info('Successful close device')

    def out_on(self):

        self._inst.write("SOUT0")
        self._inst.read_bytes(3)
        self.ready = True

    def out_off(self):

        self._inst.write("SOUT1")
        self._inst.read_bytes(3)
        self.ready = False

    def write_voltage(self, voltage_V):
        """update voltage value """

        mini, maxi = self.get_voltage_limit()

        if mini <= voltage_V <= maxi:
            voltage = voltage_V * 10
            # voltage = min(max(0, int(voltage_V * 10)), int(self._voltage_max * 10))
            self._inst.write("VOLT%03d" % voltage)
            self._inst.read_bytes(3)
        else:
            self.log.warning(f'Voltage value {voltage_V} V out of range')

    def write_current(self, current_A):
        """ update current value"""
        mini, maxi = self.get_current_limit()
        if mini <= current_A <= maxi:
            current = current_A * 100
            # current = min(max(0, int(current_A * 100)), int(self._current_max * 100))
            self._inst.write("CURR%03d" % current)
            self._inst.read_bytes(3)
        else:
            self.log.warning(f'Current value {current_A} A out of range')

    def get_voltage(self):
        """ """
        self.out_on()
        if self.ready == True:
            self._inst.write("GETD")
            getd = self._inst.read_bytes(13)
            self._voltage = int(getd[0:4]) / 100.0
            # self.read_raw(1)

        #self.out_off()
        return self._voltage

    def get_current(self):
        """ """
        self.out_on()
        if self.ready == True:
            self._inst.write("GETD")
            getd = self._inst.read_bytes(13)
            self._current = int(getd[4:8]) / 100.0
            # self.read_raw(1)

        #self.out_off()
        return self._current

    def get_mode(self):
        self.out_on()
        if self.ready == True:
            self._inst.write("GETD")
            getd = self._inst.read_bytes(13)
            self.mode = 'CC' if int(getd[8]) else 'CV'

        #self.out_off()
        return self.mode

    def set_control_value(self, value, mini, maxi):
        """ Set control value, here heating power.

            @param flaot value: control value
        """

        if mini <= value <= maxi:
            return value
        else:
            self.log.error('{} out of range'.format(value))

    def get_control_value(self):
        pass

    def get_control_unit(self):
        """ Get unit of control value.

            @return tuple(str): short and text unit of control value
        """
        return 'V', 'Volt'

    #
    def get_voltage_limit(self):

        """ Get minimum and maximum of control value.

            @return tuple(float, float): minimum and maximum of control value
        """
        return self._voltage_min, self._voltage_max

    def get_current_limit(self):
        pass
        """ Get minimum and maximum of control value.

            @return tuple(float, float): minimum and maximum of control value
        """
        return 0, self._current_max

    def reset_value(self):
        #mode = self.get_mode()
        #self.out_on()
        self.write_current(0)
        self.write_voltage(1)
        #self.out_off()

    def get_control_limit(self):
        pass
