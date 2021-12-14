# -*- coding: utf-8 -*-
"""
This file contains the Qudi logic class for generic lock-in amplifier.

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

from core.module import Connector
from logic.generic_logic import GenericLogic
from qtpy import QtCore


class LockInLogic(GenericLogic):
    """
    This logic module doing some logic for lock-ins.
    For this simple case for SR830 we are only interested to fetch some data.
    """

    _modclass = 'lockinlogic'
    _modtype = 'logic'

    # declare connectors
    lock_in = Connector(interface='SimpleDataInterface')

    signal_measurement_finished = QtCore.Signal()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._lock_in = self.lock_in()

    def on_deactivate(self):
        """
        Deinitialisation performed during deactivation of the module.
        """
        pass

    def get_data(self):
        return self._lock_in.getData()

    # def move_abs(self, pos_mm):
    #     """ Rotate selected axis to absolute value.
    #
    #     @param param_dict: dictionary containing axis and angle
    #     """
    #     constraints = self.get_constraints()
    #     if constraints[0] <= pos_mm <= constraints[1]:
    #         self._delay_line.move_abs(pos_mm)
    #         # self.wait_until_stop()
    #         self.signal_movement_finished.emit()
    #     else:
    #         self.log.warning("Cannot move because it would be beyond constraints.")
    #
    # def move_rel(self, pos_rel_mm):
    #     """ Rotate selected axis by relative value.
    #
    #     @param param_dict: dictionary containing axis and angle
    #     """
    #     constraints = self.get_constraints()
    #     current_position = self.get_pos()
    #     if constraints[0] <= current_position + pos_rel_mm <= constraints[1]:
    #         self._delay_line.move_abs(current_position + pos_rel_mm)
    #         # self.wait_until_stop()
    #         self.signal_movement_finished.emit()
    #     else:
    #         self.log.warning("Cannot move because it is outside constraints.")
    #
    # def get_pos(self, param_dict=None):
    #     """ Gets the position of all or a specific axis.
    #
    #     @param param_dict: dictionary containing axis and angle
    #     """
    #     return self._delay_line.get_pos(param_dict)
    #
    # def wait_until_done(self, param_dict=None):
    #     """ Waits until all axes are stopped
    #     """
    #     self._delay_line.wait_until_done(param_dict)
    #
    # def home(self):
    #     """Homes by calling hardware module"""
    #     self._delay_line.home()
    #
    # def get_constraints(self):
    #     """Asking for constrains (minimal and maximal positions) by hardware module"""
    #     return self._delay_line.get_constraints()
    #
    # def measurement_movement(self, start_mm, stop_mm, step_mm, measure_time, relaxation_time_s, repeats):
    #     """ Typical movement sequence for delay line in pump-probe experiments
    #      it emits a signal when measurement should be performed
    #
    #     @param float start_mm: start position of the delay line
    #     @param float stop_mm: final requested position od the delay line
    #     @param float step_mm: step of the movement
    #     @param float relaxation_time_s: dead wait time after movement is finished at each
    #      position to reduce mechanical vibration effects
    #     @param int repeats: how many times something is measured at each point of the delay line
    #     """
    #
    #     for i in np.arange(start_mm, stop_mm+step_mm, step_mm):  # stop_mm+step_mm to include stop_mm in the range
    #         self.move_abs(i)
    #         time.sleep(relaxation_time_s)
    #         for j in range(repeats):
    #             time.sleep(measure_time)
    #             self.log.info(f"I'm at position {i} and this is my {j} measurement")
    #
    # def calibrate(self, param_dict):
    #     """ Set zero for specified axis.
    #
    #     @param param_dict: dictionary containing axis and angle
    #     """
    #     self._rotator.calibrate(param_dict)
    #
    # def get_number_of_axes(self):
    #     """ Get a number of active axes
    #
    #     @return int: number of active axes
    #     """
    #     return len(self._rotator._device_dictionary)
    #
    # def get_axes_labels(self):
    #     """ Get a labels of the axes
    #
    #     @return list: number of active axes
    #     """
    #     return list(self._rotator._device_dictionary.keys())