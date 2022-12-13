# -*- coding: utf-8 -*-
"""
This file contains a gui to communicate with Mantigora HV-2000P

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

import os
import time

from core.module import Connector
from gui.guibase import GUIBase
from qtpy import QtWidgets
from qtpy import QtCore
from qtpy import uic


class MantigoraWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'Mantigora_gui_test.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class MantigoraGui(GUIBase):
    """
    """

    # declare connectors
    hv_logic = Connector(interface='GenericLogic')
    savelogic = Connector(interface='SaveLogic')

    sigStopCounter = QtCore.Signal()
    free = True
    _mw = None
    _logic = None

    def __init__(self, config, **kwargs):

        # load connection
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors.
        """

        self._logic = self.hv_logic()
        self._save_logic = self.savelogic()

        self._logic.sigDataChanged.connect(self.update_read_data, QtCore.Qt.QueuedConnection)

        self._mw = MantigoraWindow()

        #   declare labels
        self._mw.HVPS_label.setText('HVPS type:  ' + str(self._logic._lname))
        self._mw.Serial_label.setText('Serial number = ' + str(self._logic._Serial))
        self._mw.monitor_voltage_label.setText('Output voltage, V:')
        self._mw.monitor_current_label.setText('Output current, uA:')
        self._mw.Set_voltage_label.setText('Output high voltage, V =')
        self.check_connections()

        # Change value
        self._mw.set_voltage_spinBox.lineEdit().returnPressed.connect(self.change_value)
        self._mw.set_voltage_spinBox.setRange(self._logic._Vmin, self._logic._Vmax)
        self._mw.set_voltage_spinBox.setSingleStep(1)

        # Buttons
        self._mw.update_pushButton.clicked.connect(self._update)
        self._mw.reset_pushButton.pressed.connect(self._reset)
        self._mw.close_pushButton.pressed.connect(self.closeTab)

        # start reading U and I from device
        # self.read_values()

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        # FIXME: !
        self._logic.free = False
        self._mw.close()

    def change_value(self):
        self._mw.Set_voltage_label.setText('Output high voltage, V = ' + str(self._mw.set_voltage_spinBox.value()))
        volt = self._mw.set_voltage_spinBox.value()
        self._logic.set_voltage(volt)

    def read_values(self):
        if self._logic.active:
            self._logic.sigReader.emit()

    @QtCore.Slot()
    def update_read_data(self):
        I, U = self._logic._out_current, self._logic._out_voltage
        self._mw.voltage_lcdNumber.display(U)
        self._mw.current_lcdNumber.repaint()
        self._mw.current_lcdNumber.display(I)

    def closeTab(self):
        self._logic.free = False
        time.sleep(0.7)
        self._logic.close()
        self.check_connections()

    def check_connections(self):
        if self._logic.active:
            self._logic.free = False
            self._mw.USB_connect_label.setText('USB connect: Yes')
            self._mw.USB_connect_label.setStyleSheet('color: Green')
            self.read_values()

        else:
            self._mw.USB_connect_label.setText('USB connect: No')
            self._mw.USB_connect_label.setStyleSheet('color: Red')

    def _update(self):
        if self._logic.active:
            self._logic.free = False
            time.sleep(0.7)
            self._logic.update_voltage()
            time.sleep(0.7)
            self._logic.free = True
            self.read_values()

    def _reset(self):
        if self._logic.active:
            self._logic.free = False
            time.sleep(0.7)
            self._mw.set_voltage_spinBox.setValue(10)
            self._logic.do_reset()
            time.sleep(0.7)
            self._logic.free = True
            self.read_values()
