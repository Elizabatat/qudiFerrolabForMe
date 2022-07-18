# -*- coding: utf-8 -*-
"""
This file contains the qudi logic class for the gaussmeter.
Tested only with Model 425 Lakeshore

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
from core.util.mutex import Mutex


class GaussmeterLogic(GenericLogic):
    """
    This logic module doing some logic for gaussmeters.
    """

    _modclass = 'gaussmeterlogic'
    _modtype = 'logic'

    # declare connectors
    gaussmeter = Connector(interface='SimpleDataInterface')

    # declare signals
    sigReadField = QtCore.Signal()  # used to update data

    def __init__(self, *args, **kwargs):
        """
        """
        super().__init__(*args, **kwargs)

        self._gaussmeter = None

        # locking for thread safety
        self.threadlock = Mutex()

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._gaussmeter = self.gaussmeter()

        self.sigReadField.connect(self.get_data, QtCore.Qt.QueuedConnection)

    def on_deactivate(self):
        """
        De-initialisation performed during deactivation of the module.
        """
        if self.module_state() == 'locked':
            self.module_state().unlock()

    @QtCore.Slot()
    def get_data(self):
        with self.threadlock:
            data = self._gaussmeter.getData()
            self.log.debug(f' Field is {data} T')
            # self._gaussmeter.wait(1)
            return data

    def run_data(self, n):
        for i in range(n):
            self.sigReadField.emit()
