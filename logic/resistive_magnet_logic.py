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

from core.module import Connector, StatusVar
from logic.generic_logic import GenericLogic


class ResistiveMagnetLogic(GenericLogic):

    powersource = Connector(interface='ProcessControlInterface')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        self._magnet = self.powersource()

    def on_deactivate(self):
        if self.module_state() == 'locked':
            self.module_state().unlock()

    def test(self):
        self.log.info('passed')

    def set_current(self, current):
        self._magnet.set_current_a(current)

    def set_field(self, field):
        pass

    def get_field(self):
        """Interpolates from calibration table"""
        # np.interp(0.75, np.array([0, 1, 2]), np.array([2, 3, 4]))
        pass
    def output_on(self):
        self._magnet.output_on()

    def output_off(self):
        self._magnet.output_off()

    def perform_calibration(self):
        pass

    def load_calibration(self):
        pass
