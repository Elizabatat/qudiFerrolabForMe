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

import math
import pathlib
import time
from dataclasses import dataclass
import ftd2xx as ftd
from typing import List
from serial import EIGHTBITS, PARITY_NONE, STOPBITS_ONE
import logging
from collections import OrderedDict
from core.module import Base
from interface.process_control_interface import ProcessControlInterface
from core.configoption import ConfigOption

logger = logging.root


class HighVoltage(Base, ProcessControlInterface):
    """ Hardware module for high voltage generator HV-2000P (Mantigora).

         Example config :
             HV:
        module.Class: 'high_voltage.Mantigora_HV.HighVoltage'
        code_of_max_voltage_ADC: 4000
        code_of_max_voltage_DAC: 64000
        max_voltage_V:  2000.
        min_voltage_V: 10.
        voltage_step_V: 1.
        current_step_mcA: 1.
        polarity: "P"
        sensor_resistance_kohm: 5.
        feedback_resistanse_Mohm: 	100.
        current_min_mcA: 5.
        current_max_mcA: 800.
        current_units: "micro"
              {'type': 5, 'id': 67330049, 'description': b'HV2000P', 'serial': b'1606'}
         """

    name = "HV-2000P"
    _codemax_ADC = ConfigOption('code_of_max_voltage_ADC', missing='error')
    _codemax_DAC = ConfigOption('code_of_max_voltage_DAC', missing='error')
    _voltage_max = ConfigOption('max_voltage_V', missing='error')
    _voltage_min = ConfigOption('min_voltage_V', missing='error')
    _voltage_step = ConfigOption('voltage_step_V', missing='error')
    _current_step = ConfigOption('current_step_mcA', missing='error')
    _polarity = ConfigOption('polarity', missing='error')
    _sensor_resistance = ConfigOption('sensor_resistance_kohm', missing='error')
    _feedback_resistanse = ConfigOption('feedback_resistanse_Mohm', missing='error')
    _current_min = ConfigOption('current_min_mcA', missing='error')
    _current_max = ConfigOption('current_max_mcA', missing='error')
    _current_units = ConfigOption('current_units', missing='error')

    DeviceData = {"_codemax_ADC": _codemax_ADC, "_codemax_DAC": _codemax_DAC, "_voltage_max": _voltage_max,
                  "_voltage_min": _voltage_min, "_voltage_step": _voltage_step, "_current_step": _current_step,
                  "_polarity": _polarity, "_sensor_resistance": _sensor_resistance,
                  "_feedback_resistanse": _feedback_resistanse,
                  "_current_min": _current_min, "_current_max": _current_max, "_current_units": _current_units}

    port = None
    is_open = False

    FTD_TIMEOUT = 400  # Timeout for D2XX read/write (msec)
    MANUFACTUTER = "Mantigora"  # See Unit1.pas

    SET_CODE = 0x01
    UPDATE_CODE = 0x02
    RESET_CODE = 0x03
    RESERVE_CODE = 0x04
    GET_CODE = 0x05

    max_voltage = int
    voltage_coeff = 32.
    voltage_cf = float
    current_cf = float
    current_cf = None

    def on_activate(self):

        self.port = ftd.open(0)  # Open first FTD2XX device
        self.port.setBaudRate(38400)
        self.port.setTimeouts(self.FTD_TIMEOUT, self.FTD_TIMEOUT)

        # print(self.port.getDeviceInfo())

        self.init_coefficient()
        self.is_open = True
        logger.info("Open serial port for {}".format(self))

    def on_deactivate(self):
        self.reset_value()
        self.port.close()
        self.is_open = False
        logger.info("Close serial port for {}".format(self))

    def write(self, code: int, data: List[int] = None):
        try:
            temp = bytes([code] + data) if data is not None else bytes([code])
            # logger.info("Write {}".format(temp))
            self.port.write(temp)
            # logger.info("Write method get code : {}, data : {}".format(code, data))
            # logger.info("Write {}".format(temp))
        except Exception:
            self.is_open = False
            logger.warning("cannot write".format(self))

    def read(self, nbytes) -> List[int]:
        s = self.port.read(nbytes)
        logger.debug("Read {}".format(s))
        result = [ord(c) for c in s] if type(s) is str else list(s)
        logger.debug("Convert read to {}".format(result))
        return result

    def init_coefficient(self):
        self.voltage_cf = 32.  # for HV-2000P
        self.current_cf = None

    def set_value(self, volt, curr):

        coeff_v = self._codemax_DAC / 2000.
        logger.info("Write {} V".format(volt, curr))

        if not math.isclose(coeff_v, self.voltage_cf, abs_tol=1e-2):
            logging.root.warning("Voltage coefficients not consistent {}, {}".format(coeff_v, self.voltage_cf))

        voltage = round(volt * coeff_v)
        first_byte_U = voltage - math.trunc(voltage / 256) * 256
        second_byte_U = math.trunc(voltage / 256)
        print(first_byte_U, second_byte_U)

        coeff_c = self._codemax_DAC / self._current_max

        if self.current_cf is not None:
            if not math.isclose(coeff_c, self.current_cf, abs_tol=1e-2):
                logging.root.warning("Current coefficients not consistent {}, {}".format(coeff_c, self.current_cf))

        current = round(curr * coeff_c)
        first_byte_I = current - math.trunc(current / 256) * 256
        second_byte_I = math.trunc(current / 256)
        print(first_byte_I, second_byte_I)

        if second_byte_U < 125:  # 88 is for 700V
            self.write(self.SET_CODE, [first_byte_U, second_byte_U,
                                       first_byte_I, second_byte_I])
        else:
            logger.error('too high voltage {} '.format(volt))

    def update_value(self):
        self.write(self.UPDATE_CODE)
        logger.info("successful update")

    def reset_value(self):
        self.write(self.RESET_CODE)
        logger.info("successful reset")

    def get_IU(self):
        """
        Return Current (microA or milliA) and Voltage (V)
        """
        self.write(self.GET_CODE)
        temp = self.read(5)

        if temp is None or len(temp) < 5:
            print("Can not get data from device, data_array={}".format(str(temp)))
            return 0, 0
        if temp[4] != 13:
            print("Bad read: ", temp)
            return 0, 0

        ADC_mean_count = 16
        U = (temp[2] * 256 + temp[3]) * self._voltage_max / self._codemax_ADC / ADC_mean_count
        # Return absolute value
        I = (temp[0] * 256 + temp[1]) * self._current_max / self._codemax_DAC

        if self._current_units == "micro":
            I = I - abs(U / self._feedback_resistanse)
        elif self.data.current_units == "milli":
            I = I / 1000

        return I, U

    def get_control_limit(self):
        """ Get minimum and maximum of control value.
               @return tuple(float, float): minimum and maximum of control value
               """
        return self._voltage_min, (self._voltage_max - 1000.)

    def set_control_value(self, value):
        """ Set control value, here heating power.

            @param flaot value: control value
        """
        mini, maxi = self.get_control_limit()
        if mini <= value <= maxi:
            return value

        else:
            self.log.error('Voltage value {} out of range'.format(value))

    def get_control_unit(self):
        pass

    def get_control_value(self):
        pass
