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

from core.module import Connector, StatusVar
from logic.generic_logic import GenericLogic
from qtpy import QtCore


class HighVoltageLogic(GenericLogic):
    hardware = Connector(interface='ProcessControlInterface')
    savelogic = Connector(interface='SaveLogic')

    _set_current = StatusVar(default=5)
    _set_voltage = StatusVar(default=10)
    _out_voltage = 0
    _out_current = 0

    write_data = False
    update_data = False
    active = False
    _lname = None
    _Vmax = None
    _Vmin = None
    _Serial = 1606
    free = True

    sigReader = QtCore.Signal()
    sigDataChanged = QtCore.Signal()

    def on_activate(self):

        self._hardware = self.hardware()
        self._save_logic = self.savelogic()

        self.active = self._hardware.is_open
        self._lname = self._hardware.name
        self._Vmax = self._hardware._voltage_max
        self._Vmin = self._hardware._voltage_min

        self.sigReader.connect(self.reader, QtCore.Qt.QueuedConnection)

    def on_deactivate(self):
        """ Deactivate logic module """
        self.active = self._hardware.is_open
        self.sigReader.disconnect()

    def close(self):
        """ disables the device without disabling the application """

        self.sigReader.disconnect()
        self._hardware.on_deactivate()
        self.active = self._hardware.is_open

    def set_voltage(self, volt):

        self._hardware.init_coefficient()
        self._set_voltage = self._hardware.set_control_value(volt)
        self._hardware.set_value(self._set_voltage, self._set_current)
        self.write_data = True

    def update_voltage(self):

        if self.write_data:
            self._hardware.update_value()
            self.write_data = False

    def do_get_IU(self):
        """Get voltage and current"""

        if self.active:
            self._out_current, self._out_voltage = self._hardware.get_IU()
            # print("I = {} , U = {}".format(self._out_current, self._out_voltage))
            return self._out_current, self._out_voltage

    def do_reset(self):
        """Turn off. set voltage at 0"""

        if self.active:
            self._hardware.reset_value()

    def do_loop(self, volt):
        self._set_voltage = volt
        print(self._set_voltage)
        self.set_voltage(volt)
        self.update_voltage()
        self.sigReader.emit()


    @QtCore.Slot()
    def reader(self):
        if self.free == True:

            self.do_get_IU()
            time.sleep(0.5)
            self.sigDataChanged.emit()
            self.sigReader.emit()
