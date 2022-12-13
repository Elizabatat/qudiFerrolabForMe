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


class PowerSupplyLogic(GenericLogic):
    hardware = Connector(interface='ProcessControlInterface')
    savelogic = Connector(interface='SaveLogic')

    _set_current = StatusVar(default=0)
    _set_voltage = StatusVar(default=0)
    _out_voltage = 0
    _out_current = 0

    write_data = False
    update_data = False
    active = False
    _free = False
    lmode = ''


    sigReader = QtCore.Signal()
    sigDataChanged = QtCore.Signal()

    def on_activate(self):

        self._hardware = self.hardware()
        self._save_logic = self.savelogic()

        self.active = self._hardware.is_open

        self.sigReader.connect(self.reader, QtCore.Qt.QueuedConnection)
        self.lmode = self._hardware.get_mode()


    def on_deactivate(self):

        self.active = False
        self.sigReader.disconnect()

    def close(self):
        self._hardware.on_deactivate()
        self.active = self._hardware.is_open

    def set_voltage(self, volt):

        mini, maxi = self._hardware.get_voltage_limit()
        self._hardware.out_on()
        self._set_voltage = self._hardware.set_control_value(volt,mini, maxi)
        self.write_data = True
        self.log.info('Success set voltage'.format(self._set_voltage))
        self._hardware.out_off()

        return self._set_voltage


    def update_voltage(self):
        if self.write_data == True:
            self._hardware.write_voltage(self._set_voltage)
            self.write_data = False

    def set_current(self, curr):

        mini, maxi = self._hardware.get_current_limit()
        print(mini, maxi)
        self._hardware.out_on()
        self._set_current = self._hardware.set_control_value(curr, mini, maxi)
        self.write_data = True
        self.log.info('Success set current'.format(self._set_current))
        #self._hardware.out_off()

        return self._set_current

    def update_current(self):
        if self.write_data == True:
            self._hardware.write_current(self._set_current)
            self.write_data = False

    def do_get_IU(self):
        """Get voltage and current"""

        if self.active == True:
            self._out_current = self._hardware.get_current()
            self._out_voltage = self._hardware.get_voltage()
            print("I = {} , U = {}".format(self._out_current, self._out_voltage))
            return self._out_current, self._out_voltage

    def do_reset(self):
        """Turn off. set voltage at 0"""
        if self.active == True:
            self._hardware.reset_value()

    @QtCore.Slot()
    def reader(self):
        if self.free == True:
            print("good")
            self.do_get_IU()
            time.sleep(0.5)
            self.sigDataChanged.emit()
            self.sigReader.emit()
