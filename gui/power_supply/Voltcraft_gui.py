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
import sys

import time

from PyQt5.QtWidgets import QSlider

from core.module import Connector
from core.configoption import ConfigOption
from gui.guibase import GUIBase
from gui.colordefs import QudiPalettePale as palette
from qtpy import QtWidgets
from qtpy import QtCore
from qtpy import QtGui
from qtpy import uic


class VoltcraftWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'voltcraft.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class VoltcraftGui(GUIBase):
    """
    """

    # declare connectors
    ps_logic = Connector(interface='GenericLogic')
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

        self._logic = self.ps_logic()
        self._save_logic = self.savelogic()

        self._logic.sigDataChanged.connect(self.update_read_data, QtCore.Qt.QueuedConnection)

        self._mw = VoltcraftWindow()

        #   declare labels
        self._mw.set_current_label.setText('Set current, A = ')
        self._mw.set_voltage_label.setText('Set voltage, V = ')

        self._mw.regim_label.setText('Mode  ' + str(self._logic.lmode))

        #self.check_connections()
        self.set_mode()

        # Change value
        # self._mw.set_voltage_spinBox.valueChanged.connect(self.change_value)
        #self._mw.set_voltage_spinBox.editingFinished.connect(self.change_value)
        self._mw.set_voltage_DoubleSpinBox.lineEdit().returnPressed.connect(self.change_voltage)
        self._mw.set_voltage_DoubleSpinBox.setRange(1, 60)
        self._mw.set_voltage_DoubleSpinBox.setSingleStep(0.1)

        self._mw.set_current_DoubleSpinBox.lineEdit().returnPressed.connect(self.change_current)
        self._mw.set_current_DoubleSpinBox.setRange(0, 2)
        self._mw.set_current_DoubleSpinBox.setSingleStep(0.1)



        # Buttons
        self._mw.set_pushButton.clicked.connect(self._update)
        self._mw.reset_pushButton.pressed.connect(self._reset)
        self._mw.close_pushButton.pressed.connect(self.closeTab)


    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        # FIXME: !
        self._logic.free = False
        self._mw.close()

    def set_mode(self):
        if self._logic.lmode == 'CV':
             self._mw.set_current_DoubleSpinBox.setEnabled(False)
        elif self._logic.lmode == 'CC':
             self._mw.set_voltage_DoubleSpinBox.setDisabled(True)

    def change_voltage(self):
        self._mw.set_voltage_label.setText('Set voltage, V = ' + str(self._mw.set_voltage_DoubleSpinBox.value()))
        volt = self._mw.set_voltage_DoubleSpinBox.value()
        self._logic.set_voltage(volt)
        #self.read_values()

    def change_current(self):
        self._mw.set_current_label.setText('Set current, A = ' + str(self._mw.set_current_DoubleSpinBox.value()))
        curr = self._mw.set_current_DoubleSpinBox.value()
        self._logic.set_current(curr)
        #self.read_values()


    def read_values(self):
        if self._logic.active:
            self._logic.sigReader.emit()

    @QtCore.Slot()
    def update_read_data(self):
        I, U = self._logic._out_current, self._logic._out_voltage
        self._mw.out_voltage_lcdNumber.display(U)
        #self._mw.current_lcdNumber.repaint()
        self._mw.out_current_lcdNumber.display(I)


    def closeTab(self):
        self._logic.close()

    # def check_connections(self):
    #     if self._logic.active:
    #         self._logic.free = False
    #         self._mw.USB_connect_label.setText('USB connect: Yes')
    #         self._mw.USB_connect_label.setStyleSheet('color: light Green')
    #
    #     else:
    #         self._mw.USB_connect_label.setText('USB connect: No')
    #         self._mw.USB_connect_label.setStyleSheet('color: Red')

    def _update(self):
        print("good")
        if self._logic.active:
            self._logic.free = False
            time.sleep(1)
            if self._logic.lmode == 'CV':
                self._logic.update_voltage()
            elif self._logic.lmode == 'CC':
                self._logic.update_current()

            time.sleep(1)
            self._logic.free = True
            self.read_values()


    def _reset(self):
        print("reset")
        if self._logic.active:
            self._logic.free = False
            time.sleep(1)
            self._logic.do_reset()
            time.sleep(1)
            self._logic.free = True
            self.read_values()

