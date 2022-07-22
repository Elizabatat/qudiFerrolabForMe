# -*- coding: utf-8 -*-

"""
This file contains the general logic for resistive magnet control.
Highly experimental.

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

import numpy as np
import time

from core.module import Connector, StatusVar
from logic.generic_logic import GenericLogic
from qtpy import QtCore

from core.configoption import ConfigOption


class ResistiveMagnetLogic(GenericLogic):

    # declare connectors
    powersource = Connector(interface='ProcessControlInterface')
    arduino_relay_logic = Connector(interface='GenericLogic')
    magnetometer_logic = Connector(interface='GenericLogic')
    savelogic = Connector(interface='SaveLogic')

    _last_current = 0.0

    # declare signals
    sigPolarityChangeRequested = QtCore.Signal(str, str)

    # config options
    _magnet_calibration_path = ConfigOption('magnet_calibration_path', default=None, missing='error')

    # status variables
    calibration_data = StatusVar(default=None)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self._magnet = None
        self._relay_logic = None
        self._magnetometer_logic = None
        self._save_logic = None

    def on_activate(self):
        self._magnet = self.powersource()
        self._relay_logic = self.arduino_relay_logic()
        self._magnetometer_logic = self.magnetometer_logic()
        self._save_logic = self.savelogic()

        # connect signals
        self.sigPolarityChangeRequested.connect(self._relay_logic.set_state)

    def on_deactivate(self):
        if self.module_state() == 'locked':
            self.module_state().unlock()

        self.sigPolarityChangeRequested.disconnect()

    def test(self):
        self.log.info('passed')

    def set_voltage(self, voltage):
        self._magnet.set_voltage_v(voltage)

    def get_voltage(self):
        return self._magnet.get_voltage_v()

    def set_current(self, requested_current):
        # TODO: current protection or smth
        name = self._relay_logic.device_name()
        state = self._relay_logic.get_state(name)
        self._last_current = self.get_current()

        if requested_current > 0:
            if state == 'positive':
                self._magnet.set_current_a(requested_current)
            elif state == 'negative':
                self._magnet.set_current_a(0.0)
                time.sleep(0.7)
                self.sigPolarityChangeRequested.emit(name, 'positive')
                time.sleep(0.3)
                self._magnet.set_current_a(requested_current)
        elif requested_current < 0:
            if state == 'positive':
                self._magnet.set_current_a(0.0)
                time.sleep(0.7)
                self.sigPolarityChangeRequested.emit(name, 'negative')
                time.sleep(0.3)
                self._magnet.set_current_a(abs(requested_current))
            elif state == 'negative':
                self._magnet.set_current_a(abs(requested_current))
        else:
            self._magnet.set_current_a(0.0)

    def get_current(self):
        """Gets current from the power source emulating negative sign by checking the state of the relay"""
        state = self._relay_logic.get_state(self._relay_logic.device_name())
        if state == 'positive':
            current = self._magnet.get_current_a()
        elif state == 'negative':
            current = -self._magnet.get_current_a()
        return current

    def set_field(self, field):
        pass

    def get_field(self):
        """Interpolates field value (in tesla) from the calibration table statusVar.
        We will split calibration in two branches, bottom and top one"""

        currents = self.calibration_data['current (A)']
        fields = self.calibration_data['field (T)']

        currents_bottom = currents[0:currents.size // 2 + 1]
        currents_top = currents[currents.size//2:]

        fields_bottom = fields[0:fields.size // 2 + 1]
        fields_top = fields[fields.size//2:]

        return [np.interp(self.get_current(), currents_bottom, fields_bottom),
                np.interp(self.get_current(), np.flip(currents_top), np.flip(fields_top))]

    def _get_branch(self):
        """Helper function for the determination on which branch we are sitting"""
        current = self.get_current()
        if current > self._last_current:
            self.log.info('We are on a bottom one')
        elif current < self._last_current:
            self.log.info('We are on a top branch')

    def output_on(self):
        self._magnet.output_on()

    def output_off(self):
        self._magnet.output_off()

    def automatic_calibration(self, start_current, end_current, step_current, wait_s):
        """Doing a loop over set of currents (in amperes), recording field values in the process.
            Calibration is performed from fully magnetized state aka maximal negative current."""

        steps_number = np.rint(abs(start_current - end_current) / step_current)
        currents = np.linspace(start_current, start_current + step_current * steps_number, int(steps_number + 1))

        current_loop = np.concatenate([currents, -currents])
        currents[np.abs(currents) < 0.00001] = 0  # hack to fix dirty float output

        fields = np.zeros(currents.size)

        for i, current in enumerate(currents):
            self.set_current(current)
            time.sleep(wait_s)
            fields[i] = self._magnetometer_logic.get_data()

        self.set_current(0)

        self.calibration_data = dict({'current (A)': currents,
                                      'field (T)': fields
                                      })

        time.sleep(0.3)
        self.save_calibration()

    def save_calibration(self):
        """
        :param string name_tag: postfix name tag for saved filename.
        :param OrderedDict custom_header:
        :return:
            This ordered dictionary is added to the default data file header. It allows arbitrary
            additional experimental information to be included in the saved data file header.
        """
        filepath = self._save_logic.get_path_for_module(module_name='resistive_magnet')

        # TODO: parameters
        # parameters = OrderedDict()
        # parameters['Pump power (mW)'] = self._pump_power_mW
        # parameters['Pump wavelength (nm)'] = self._pump_wavelength_nm

        self._save_logic.save_data(self.calibration_data,
                                   filepath=filepath,
                                   filelabel='Magnet_calibration'
                                   )

        self.log.debug('Calibration saved to:\n{0}'.format(filepath))

    def _init_calibration_data(self):
        pass

    def load_calibration(self):
        """Reads calibration data from a file specified in configuration"""
        calibration_table = np.genfromtxt(self._magnet_calibration_path).transpose()
        self.calibration_data = dict({'current (A)': calibration_table[0],
                                      'field (T)': calibration_table[1]
                                      })


