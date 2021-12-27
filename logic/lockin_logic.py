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
import datetime as dt

from core.module import Connector
from logic.generic_logic import GenericLogic
from qtpy import QtCore
from core.util.mutex import Mutex


class LockInLogic(GenericLogic):
    """
    This logic module doing some logic for lock-ins.
    For this simple case for SR830 we are only interested to fetch some data.
    """

    _modclass = 'lockinlogic'
    _modtype = 'logic'

    # declare connectors
    lock_in = Connector(interface='SimpleDataInterface')

    sigStatusChanged = QtCore.Signal(bool, bool)
    _sigNextDataFrame = QtCore.Signal()  # internal signal

    def __init__(self, *args, **kwargs):
        """
        """
        super().__init__(*args, **kwargs)

        self.threadlock = Mutex()
        self._stop_requested = True

        self._recorded_data = None
        self._data_recording_active = False

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._lock_in = self.lock_in()

        self._data_recording_active = False
        self._stop_requested = True

        self._sigNextDataFrame.connect(self.acquire_data_block, QtCore.Qt.QueuedConnection)

    def on_deactivate(self):
        """
        Deinitialisation performed during deactivation of the module.
        """
        if self.module_state() == 'locked':
            self._stop_reader_wait()

        self._sigNextDataFrame.disconnect()

        pass

    def get_data(self):
        return self._lock_in.getData()

    @QtCore.Slot()
    def start_reading(self):
        """
        Start data acquisition loop.

        @return error: 0 is OK, -1 is error
        """
        with self.threadlock:
            # Lock module
            if self.module_state() == 'locked':
                self.log.warning('Data acquisition already running. "start_reading" call ignored.')
                self.sigStatusChanged.emit(True, self._data_recording_active)
                return 0

            self.module_state.lock()
            self._stop_requested = False

            self.sigStatusChanged.emit(True, self._data_recording_active)

            # if self._data_recording_active:
            #     self._record_start_time = dt.datetime.now()
            #     self._recorded_data = list()

            # if self._lock_in.start_stream() < 0:
            #     self.log.error('Error while starting streaming device data acquisition.')
            #     self._stop_requested = True
            #     self._sigNextDataFrame.emit()
            #     return -1

            self.log.info("trace started")
            self._sigNextDataFrame.emit()
        return 0

    @QtCore.Slot()
    def stop_reading(self):
        """
        Send a request to stop counting.

        @return int: error code (0: OK, -1: error)
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                self._stop_requested = True
                self.module_state.unlock()
                self.sigStatusChanged.emit(False, False)
                self.log.info("trace stopped")
        return 0

    @QtCore.Slot()
    def acquire_data_block(self):
        """
        In principle this thing should repeatedly get data from lock-in
        """

        with self.threadlock:
            if self.module_state() == 'locked':
                # check for break condition
                if self._stop_requested:
                    # terminate the hardware streaming
                    if self._streamer.stop_stream() < 0:
                        self.log.error(
                            'Error while trying to stop streaming device data acquisition.')
                    if self._data_recording_active:
                        self._save_recorded_data(to_file=True, save_figure=True)
                        self._recorded_data = list()
                    self._data_recording_active = False
                    self.module_state.unlock()
                    self.sigStatusChanged.emit(False, False)
                    return

                data = self._lock_in.getData()

                # self.log.info("i'm inside acquire_next_data_frame")

                # Emit update signal
                # self.sigDataChanged.emit(*self.trace_data, *self.averaged_trace_data)
                self._sigNextDataFrame.emit()

        return

    @QtCore.Slot()
    def start_recording(self):
        pass

    @QtCore.Slot()
    def stop_recording(self):
        pass

    @property
    def data_recording_active(self):
        return self._data_recording_active
