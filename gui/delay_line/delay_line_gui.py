# -*- coding: utf-8 -*-
"""
This file contains the Qudi console GUI module.
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

from core.module import Connector
from gui.guibase import GUIBase
from qtpy import QtWidgets
from qtpy import QtCore
from qtpy import uic
import sys


class MainWindow(QtWidgets.QMainWindow):
    """ Helper class for window loaded from UI file.
    """
    def __init__(self):
        """ Create the switch GUI window.
        """
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_delay_line_gui.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class DelayLineGui(GUIBase):
    """ A graphical interface to control polarization rotators by hand and change their calibration.
    """
    _modclass = 'delay_line_gui'
    _modtype = 'gui'

    ## declare connectors
    delaylogic = Connector(interface='GenericLogic')

    # self._mw.focus_Action.triggered.connect(self._clicked)  # Start/stop focus mode

    # Playing a bit with signals
    sigDelayLineStopped = QtCore.Signal()

    def on_activate(self):
        """Create all UI objects and show the window.
        """
        self._mw = MainWindow()
        self._delay_logic = self.delaylogic()
        # get a list of active axes
        # axes_list = self._delay_logic.get_axes_labels()
        # For each active axis add a widget to the GUI to show its state
        # for axis in axes_list:
        #     frame = QtWidgets.QGroupBox(axis, self._mw.scrollAreaWidgetContents)
        #     frame.setAlignment(QtCore.Qt.AlignLeft)
        #     frame.setFlat(False)
        #     self._mw.layout.addWidget(frame)
        #     layout = QtWidgets.QVBoxLayout(frame)
        #     polar_widget = PolarizationWidget(axis, self._polar_logic)
        #     layout.addWidget(polar_widget)
        self.restoreWindowPos(self._mw)
        self.show()

        self.update_position()

        # load states of spinboxes
        self._mw.start_scan_mm_doubleSpinBox.setValue(self._delay_logic._start_scan_mm)
        self._mw.end_scan_mm_doubleSpinBox.setValue(self._delay_logic._end_scan_mm)
        self._mw.step_mm_doubleSpinBox.setValue(self._delay_logic._step_mm)
        self._mw.wait_time_s_doubleSpinBox.setValue(self._delay_logic._wait_time_s)
        self._mw.number_points_spinBox.setValue(self._delay_logic._number_points)
        self._mw.number_scans_spinBox.setValue(self._delay_logic._number_scans)

        # User actions
        self._mw.home_Action.triggered.connect(self.home)
        self._mw.update_Action.triggered.connect(self.update_position)
        self._mw.scan_Action.triggered.connect(self.do_scan)

        self.sigDelayLineStopped.connect(self.test_signal)

        # Tinkering with boxes
        self._mw.start_scan_mm_doubleSpinBox.editingFinished.connect(self.start_scan_changed)
        self._mw.delay_position_mm_doubleSpinBox.editingFinished.connect(self.position_changed)
        self._mw.end_scan_mm_doubleSpinBox.editingFinished.connect(self.end_scan_changed)
        self._mw.step_mm_doubleSpinBox.editingFinished.connect(self.step_changed)
        self._mw.wait_time_s_doubleSpinBox.editingFinished.connect(self.wait_time_changed)
        self._mw.number_points_spinBox.editingFinished.connect(self.number_points_changed)
        self._mw.number_scans_spinBox.editingFinished.connect(self.number_scans_changed)

    def test_signal(self):
        if self._mw.full_time_scan_label.isVisible():
            self._mw.full_time_scan_label.setVisible(False)
        else:
            self._mw.full_time_scan_label.setVisible(True)

    def show(self):
        """Make sure that the window is visible and at the top.
        """
        self._mw.show()

    def on_deactivate(self):
        """ Hide window and stop ipython console.
        """
        self.saveWindowPos(self._mw)
        self._mw.close()

        # Add layout that we want to fill
        # self.layout = QtWidgets.QVBoxLayout(self.scrollArea)

    def home(self):
        self._delay_logic.home()

    def update_position(self):
        self._mw.delay_position_mm_doubleSpinBox.setValue(self._delay_logic.get_pos())

# TODO: emit some kind of signal when delay line head stopped at specific point after specified wait time

# class PolarizationWidget(QtWidgets.QWidget):
#     """ A widget that shows all data associated to a polarization rotator axis.
#     """
#     def __init__(self, axis, logic):
#         """ Create a switch widget.
#           @param string axis: axis for widget, taken from logic
#           @param module? logic: reference to polarization control logic module
#         """
#         # Get the path to the *.ui file
#         this_dir = os.path.dirname(__file__)
#         ui_file = os.path.join(this_dir, 'ui_polarization_widget.ui')
#
#         # Load it
#         super().__init__()
#         uic.loadUi(ui_file, self)
#
#         # self.axis = axis
#         # self.pol_logic = logic
#
#         # correct state at start
#         # self.angle_doubleSpinBox.setValue(self.pol_logic.get_pos({self.axis})[self.axis])
#
#         # user actions
#         # self.pol_logic.signal_rotation_finished.connect(self.update_angle)
#         # self.angle_doubleSpinBox.editingFinished.connect(self.angle_changed)
#         # self.set_zero_pushButton.clicked.connect(self.set_zero)

#     def set_zero(self):
#         # self.pol_logic.calibrate({self.axis})
#         # self.angle_doubleSpinBox.setValue(self.pol_logic.get_pos({self.axis})[self.axis])
#         pass

    def position_changed(self):
        self._delay_logic.move_abs(self._mw.delay_position_mm_doubleSpinBox.value())

    def calculate_full_scan_time(self):
        pass

    def do_scan(self):
        self._delay_logic.measurement_movement(
                                               self._mw.start_scan_mm_doubleSpinBox.value(),
                                               self._mw.end_scan_mm_doubleSpinBox.value(),
                                               self._mw.step_mm_doubleSpinBox.value(),
                                               self._mw.wait_time_s_doubleSpinBox.value(),
                                               self._mw.number_points_spinBox.value(),
                                               self._mw.number_scans_spinBox.value()
                                               )
        self.update_position()
        self.sigDelayLineStopped.emit()
        pass

    def start_scan_changed(self):
        _old_parameter = self._delay_logic._start_scan_mm
        self._delay_logic._start_scan_mm = self._mw.start_scan_mm_doubleSpinBox.value()
        self.log.info(f"Changing start scan from {_old_parameter} to {self._delay_logic._start_scan_mm}")
        # self.update_data()

    def end_scan_changed(self):
        self._delay_logic._end_scan_mm = self._mw.end_scan_mm_doubleSpinBox.value()
        # self.update_data()

    def step_changed(self):
        self._delay_logic.step_mm = self._mw.step_mm_doubleSpinBox.value()
        # self.update_data()

    def wait_time_changed(self):
        self._delay_logic.wait_time_s = self._mw.wait_time_s_doubleSpinBox.value()
        # self.update_data()

    def number_points_changed(self):
        self._delay_logic.number_points = self._mw.number_points_spinBox.value()
        # self.update_data()

    def number_scans_changed(self):
        self._delay_logic.number_scans = self._mw.number_scans_spinBox.value()
        # self.update_data()

#     def update_angle(self):
#         # self.angle_doubleSpinBox.setValue(self.pol_logic.get_pos({self.axis})[self.axis])
#         pass
