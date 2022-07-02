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

    # declaring signals
    sigMoveTo = QtCore.Signal(float)

    # sigDoScan = QtCore.Signal()

    # sigDelayLineStopped = QtCore.Signal()

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
        self.update_full_scan_time()

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
        self._mw.stop_Action.triggered.connect(self.stop_scan)

        # self.sigDelayLineStopped.connect(self.test_signal)

        # Connect boxes
        self._mw.start_scan_mm_doubleSpinBox.editingFinished.connect(self.start_scan_changed)
        self._mw.delay_position_mm_doubleSpinBox.lineEdit().returnPressed.connect(self.position_changed)
        self._mw.end_scan_mm_doubleSpinBox.editingFinished.connect(self.end_scan_changed)
        self._mw.step_mm_doubleSpinBox.editingFinished.connect(self.step_changed)
        self._mw.wait_time_s_doubleSpinBox.editingFinished.connect(self.wait_time_changed)
        self._mw.number_points_spinBox.editingFinished.connect(self.number_points_changed)
        self._mw.number_scans_spinBox.editingFinished.connect(self.number_scans_changed)

        # Signals
        self.sigMoveTo.connect(self._delay_logic.move_abs, QtCore.Qt.QueuedConnection)

        # Signals from logic
        self._delay_logic.sigStatusChanged.connect(self.update_status, QtCore.Qt.QueuedConnection)
        self._delay_logic.sigDoScan.connect(self._delay_logic.do_scan, QtCore.Qt.QueuedConnection)

    def on_deactivate(self):
        """ Hide window, disconnect boxes, signals and stop ipython console.
        """

        # Disconnect Signals
        self.sigMoveTo.disconnect()

        # Signals from logic
        self._delay_logic.sigDoScan.disconnect()
        self._delay_logic.sigStatusChanged.disconnect()

        # Disconect boxes
        self._mw.start_scan_mm_doubleSpinBox.editingFinished.disconnect()
        self._mw.delay_position_mm_doubleSpinBox.lineEdit().returnPressed.disconnect()
        self._mw.end_scan_mm_doubleSpinBox.editingFinished.disconnect()
        self._mw.step_mm_doubleSpinBox.editingFinished.disconnect()
        self._mw.wait_time_s_doubleSpinBox.editingFinished.disconnect()
        self._mw.number_points_spinBox.editingFinished.disconnect()
        self._mw.number_scans_spinBox.editingFinished.disconnect()

        self.saveWindowPos(self._mw)
        self._mw.close()

        # Add layout that we want to fill
        # self.layout = QtWidgets.QVBoxLayout(self.scrollArea)

    def test_signal(self):
        if self._mw.full_time_scan_label.isVisible():
            self._mw.full_time_scan_label.setVisible(False)
        else:
            self._mw.full_time_scan_label.setVisible(True)

    def show(self):
        """Make sure that the window is visible and at the top.
        """
        self._mw.show()

    def home(self):
        self._delay_logic.home()

    def update_position(self):
        self._mw.delay_position_mm_doubleSpinBox.setValue(self._delay_logic.get_pos())

    def update_full_scan_time(self):
        scan_time = (abs(self._mw.start_scan_mm_doubleSpinBox.value() - self._mw.end_scan_mm_doubleSpinBox.value()) /
                     self._mw.step_mm_doubleSpinBox.value() *
                     self._mw.wait_time_s_doubleSpinBox.value() * self._mw.number_points_spinBox.value() *
                     self._mw.number_scans_spinBox.value()) / 60
        self._mw.full_time_scan_label.setText(f'Full scan will take {scan_time:.1f} min.')
        pass

    def do_scan(self):
        self._delay_logic.sigDoScan.emit()
        # self._delay_logic.measurement_movement(
        #                                        self._mw.start_scan_mm_doubleSpinBox.value(),
        #                                        self._mw.end_scan_mm_doubleSpinBox.value(),
        #                                        self._mw.step_mm_doubleSpinBox.value(),
        #                                        self._mw.wait_time_s_doubleSpinBox.value(),
        #                                        self._mw.number_points_spinBox.value(),
        #                                        self._mw.number_scans_spinBox.value()
        #                                        )
        # self.update_position()
        # self.sigDelayLineStopped.emit()
        pass

    def stop_scan(self):
        self._delay_logic.sigStopScan.emit()

    @QtCore.Slot(bool)
    def update_status(self, moving=None):
        """
        Updating status of the module.
        Deactivating boxes.
        """
        if moving is None:
            moving = self._lock_in_logic.module_state() == 'locked'

        self._mw.start_scan_mm_doubleSpinBox.setEnabled(not moving)
        self._mw.end_scan_mm_doubleSpinBox.setEnabled(not moving)
        self._mw.step_mm_doubleSpinBox.setEnabled(not moving)
        # self._mw.delay_position_mm_doubleSpinBox.setEnabled(not moving)  # do not disable it because it will trigger
        self._mw.wait_time_s_doubleSpinBox.setEnabled(not moving)
        self._mw.number_points_spinBox.setEnabled(not moving)
        self._mw.number_scans_spinBox.setEnabled(not moving)

        self._mw.home_Action.setEnabled(not moving)
        self._mw.update_Action.setEnabled(not moving)
        self._mw.scan_Action.setEnabled(not moving)
        self._mw.stop_Action.setEnabled(moving)

    # TODO: should refactor it to something like signal(dict) like in lock_in_gui.py

    # TODO: should make less restrictive condition to prevent attempts to move with um precision like 9.9997 to 10.0
    def position_changed(self):
        old_parameter = self._delay_logic._position_mm
        if old_parameter != self._mw.delay_position_mm_doubleSpinBox.value():
            self.sigMoveTo.emit(self._mw.delay_position_mm_doubleSpinBox.value())
            self.log.info(
                f"Changing position from {old_parameter} to {self._mw.delay_position_mm_doubleSpinBox.value()} (mm)")

    def start_scan_changed(self):
        old_parameter = self._delay_logic._start_scan_mm
        if old_parameter != self._mw.start_scan_mm_doubleSpinBox.value():
            self._delay_logic._start_scan_mm = self._mw.start_scan_mm_doubleSpinBox.value()
            self.log.info(f"Changing start scan from {old_parameter} to {self._delay_logic._start_scan_mm} (mm)")
        self.update_full_scan_time()

    def end_scan_changed(self):
        old_parameter = self._delay_logic._end_scan_mm
        if old_parameter != self._mw.end_scan_mm_doubleSpinBox.value():
            self._delay_logic._end_scan_mm = self._mw.end_scan_mm_doubleSpinBox.value()
            self.log.info(f"Changing start scan from {old_parameter} to {self._delay_logic._end_scan_mm} (mm)")
        self.update_full_scan_time()

    def step_changed(self):
        old_parameter = self._delay_logic._step_mm
        if old_parameter != self._mw.step_mm_doubleSpinBox.value():
            self._delay_logic._step_mm = self._mw.step_mm_doubleSpinBox.value()
            self.log.info(f"Changing step distance from {old_parameter} to {self._delay_logic._step_mm} (mm)")
        self.update_full_scan_time()

    def wait_time_changed(self):
        old_parameter = self._delay_logic._wait_time_s
        if old_parameter != self._mw.wait_time_s_doubleSpinBox.value():
            self._delay_logic._wait_time_s = self._mw.wait_time_s_doubleSpinBox.value()
            self.log.info(f"Changing acquisition time from {old_parameter} to {self._delay_logic._wait_time_s} (s)")
        self.update_full_scan_time()

    def number_points_changed(self):
        old_parameter = self._delay_logic._number_points
        if old_parameter != self._mw.number_points_spinBox.value():
            self._delay_logic._number_points = self._mw.number_points_spinBox.value()
            self.log.info(f"Changing number of points from {old_parameter} to {self._delay_logic._number_points}")
        self.update_full_scan_time()

    def number_scans_changed(self):
        old_parameter = self._delay_logic._number_scans
        if old_parameter != self._mw.number_scans_spinBox.value():
            self._delay_logic._number_scans = self._mw.number_scans_spinBox.value()
            self.log.info(f"Changing number of scans from {old_parameter} to {self._delay_logic._number_scans}")
        self.update_full_scan_time()