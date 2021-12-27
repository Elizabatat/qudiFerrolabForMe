# -*- coding: utf-8 -*-
"""
This file contains the Qudi logic class for the delay line controls.

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
import numpy as np

from core.module import Connector, StatusVar
from logic.generic_logic import GenericLogic
from qtpy import QtCore


class DelayLineLogic(GenericLogic):
    """
    This logic module doing some logic for delay lines.
    """

    _modclass = 'delaylinelogic'
    _modtype = 'logic'

    # declare connectors
    motor = Connector(interface='MotorInterface')

    signalMovementFinished = QtCore.Signal()

    # status variables
    _start_scan_mm = StatusVar(default=1)
    _end_scan_mm = StatusVar(default=10)
    _step_mm = StatusVar(default=1)
    _position_mm = StatusVar(default=1)
    _number_points = StatusVar(default=1)
    _number_scans = StatusVar(default=1)
    _wait_time_s = StatusVar(default=1)

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._delay_line = self.motor()

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        pass

    def move_abs(self, pos_mm):
        """ Move the delay line to absolute position in mm.

        @param float pos_mm: requested position in mm
        """
        constraints = self.get_constraints()
        if constraints[0] <= pos_mm <= constraints[1]:
            self._delay_line.move_abs(pos_mm)
            # self.wait_until_stop()
            # self.signalMovementFinished.emit()
            self._position_mm = self.get_pos()
        else:
            self.log.warning("Cannot move because it would be beyond constraints.")

    def move_rel(self, pos_rel_mm):
        """ Move the delay line to relative (current position + relative shift) position in mm.

        @param float pos_rel_mm: requested relative position
        """
        constraints = self.get_constraints()
        current_position = self.get_pos()
        if constraints[0] <= current_position + pos_rel_mm <= constraints[1]:
            self._delay_line.move_abs(current_position + pos_rel_mm)
            # self.wait_until_stop()
            # self.signalMovementFinished.emit()
            self._position_mm = self.get_pos()
        else:
            self.log.warning("Cannot move because it is outside constraints.")

    def get_pos(self, param_dict=None):
        """ Gets the position of all or a specific axis.

        @param param_dict: dictionary containing axis and angle
        """
        return self._delay_line.get_pos(param_dict)

    def wait_until_done(self, param_dict=None):
        """ Waits until all axes are stopped
        """
        self._delay_line.wait_until_done(param_dict)

    def home(self):
        """Homes by calling hardware module"""
        self._delay_line.home()

    def get_constraints(self):
        """Asking for constrains (minimal and maximal positions) by hardware module"""
        return self._delay_line.get_constraints()

    def measurement_movement(self, start_mm, stop_mm, step_mm, wait_time_s, number_points, number_scans):
        """ Typical movement sequence for delay line in pump-probe experiments
         it emits a signal when measurement should be performed

        @param float start_mm: start position of the delay line
        @param float stop_mm: final requested position of the delay line
        @param float step_mm: step of the movement
        @param float wait_time_s: wait time for lock-in
        @param int number_points: how many times something is measured at each stop point of the delay line
        @param int number_scans: how many times the scan from start to end is perfromed
        """
        for scan in range(number_scans):
            for position in np.arange(start_mm, stop_mm+step_mm, step_mm):  # stop_mm+step_mm to include end in range
                self.move_abs(position)
                for point in range(number_points):
                    time.sleep(wait_time_s)
                    self.log.info(f"I'm in the scan {scan} at {position} position, and at {point} point")
                    self.signalMovementFinished.emit()

    def set_parameter(self, par, value):
        self.log.info(f"Changing parameter {par} to value {value}")
        if par == "start_scan_mm":
            self._start_scan_mm = value
        elif par == "end_scan_mm":
            self._end_scan_mm = value
        elif par == "step_mm":
            self._step_mm = value
        elif par == "wait_time_s":
            self._wait_time_s = value
        elif par == "number_points":
            self._number_points = value
        elif par == "number_scans":
            self._number_scans = value
        else:
            pass

    # def calibrate(self, param_dict):
    #     """ Set zero for specified axis.
    #
    #     @param param_dict: dictionary containing axis and angle
    #     """
    #     self._rotator.calibrate(param_dict)

    # def get_number_of_axes(self):
    #     """ Get a number of active axes
    #
    #     @return int: number of active axes
    #     """
    #     return len(self._rotator._device_dictionary)

    # def get_axes_labels(self):
    #     """ Get a labels of the axes
    #
    #     @return list: number of active axes
    #     """
    #     return list(self._rotator._device_dictionary.keys())
