# -*- coding: utf-8 -*-
"""
This file contains the qudi logic class for generic lock-in amplifier.

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
import datetime as dt

from core.module import Connector
from logic.generic_logic import GenericLogic
from qtpy import QtCore
from core.util.mutex import Mutex
from core.statusvariable import StatusVar


class LockInLogic(GenericLogic):
    """
    This logic module doing some logic for lock-ins.
    For this simple case for SR830 we are only interested to fetch some data.
    """

    _modclass = 'lockinlogic'
    _modtype = 'logic'

    # declare connectors
    lock_in = Connector(interface='SimpleDataInterface')
    delay_logic = Connector(interface='GenericLogic')
    savelogic = Connector(interface='SaveLogic')

    data = []
    data_pos_x_y = []

    # declare signals
    sigDataChanged = QtCore.Signal(object, object)
    sigStatusChanged = QtCore.Signal(bool, bool)
    sigSettingsChanged = QtCore.Signal(dict)
    _sigNextDataFrame = QtCore.Signal()  # internal signal

    # pseudo config options
    _max_frame_rate = 10
    _calc_digital_freq = True

    # status vars
    _trace_window_size = StatusVar('trace_window_size', default=6)
    _data_rate = StatusVar('data_rate', default=10)

    def __init__(self, *args, **kwargs):
        """
        """
        super().__init__(*args, **kwargs)

        self._lock_in = None
        self._delay = None

        # locking for thread safety
        self.threadlock = Mutex()
        self._samples_per_frame = None
        self._stop_requested = True

        # Data arrays
        self._trace_data = None
        self._trace_times = None

        # for data recording
        self._recorded_data = None
        self._data_recording_active = False
        self._record_start_time = None

        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._lock_in = self.lock_in()
        self._delay = self.delay_logic()

        # Flag to stop the loop and process variables
        self._stop_requested = True
        self._data_recording_active = False
        self._record_start_time = None

        self._samples_per_frame = self.data_rate // self._max_frame_rate

        self._sigNextDataFrame.connect(self.acquire_data_block, QtCore.Qt.QueuedConnection)

        # connecting external signal
        self._delay.sigGetMeasurePoint.connect(self.test_signal_1)
        self._delay.sigDoScan.connect(self._init_data_pos_x_y)

        settings = self.all_settings
        self.configure_settings(**settings)

    def on_deactivate(self):
        """
        De-initialisation performed during deactivation of the module.
        """
        if self.module_state() == 'locked':
            self._stop_reader_wait()

        # Disconnect signals
        self._sigNextDataFrame.disconnect()
        self._delay.sigGetMeasurePoint.disconnect()

        self._data_rate = self.data_rate
        return

    @QtCore.Slot()
    def _init_data_pos_x_y(self):
        """Init array for time-dependent measurements"""
        self.data_pos_x_y = np.array([[], [], [], []])  # TODO: There should be a better way to do it

    @QtCore.Slot()
    def test_signal_1(self):
        """Some tests to """
        pos = self._delay._position_mm
        [x, y] = self._lock_in.getData()
        r = np.sqrt(x**2 + y**2)
        read_val = [pos, r, x, y]
        # self.log.info(f"Something triggered me on the lock_in side! btw {read_val}")
        self.data_pos_x_y = np.hstack((self.data_pos_x_y, np.expand_dims(read_val, 1)))

    @property
    def all_settings(self):
        return {'trace_window_size': self.trace_window_size,
                'data_rate': self.data_rate}

    def _init_data_arrays(self):
        window_size = self.trace_window_size_samples
        self._trace_data = np.zeros(
            [2, window_size])
        self._trace_data_averaged = np.zeros(
            [2, window_size])
        self._trace_times = np.arange(window_size) / self.data_rate
        self._recorded_data = list()
        return

    @property
    def trace_window_size_samples(self):
        return int(round(self._trace_window_size * self.data_rate))

    @property
    def trace_window_size(self):
        return self._trace_window_size

    @trace_window_size.setter
    def trace_window_size(self, val):
        self.configure_settings(trace_window_size=val)
        return

    @property
    def data_rate(self):
        return self.sampling_rate

    @property
    def sampling_rate(self):
        return self._lock_in.sample_rate

    # @property
    # def data_recording_active(self):
    #     return self._data_recording_active

    @property
    def trace_data(self):
        data = {ch: self._trace_data[i] for i, ch in enumerate(['X', 'Y'])}
        return self._trace_times, data

    @QtCore.Slot(dict)
    def configure_settings(self, settings_dict=None, **kwargs):
        """
        Sets the number of samples to average per data point, i.e. the oversampling factor.
        The counter is stopped first and restarted afterwards.

        @param dict settings_dict: optional, dict containing all parameters to set. Entries will
                                   be overwritten by conflicting kwargs.

        @return dict: The currently configured settings
        """
        if self.data_recording_active:
            self.log.warning('Unable to configure settings while data is being recorded.')
            return self.all_settings

        if settings_dict is None:
            settings_dict = kwargs
        else:
            settings_dict.update(kwargs)

        if not settings_dict:
            return self.all_settings

        # Flag indicating if the stream should be restarted
        restart = self.module_state() == 'locked'
        if restart:
            self._stop_reader_wait()

        with self.threadlock:
            # constraints = self.streamer_constraints
            data_rate = self.data_rate

            if 'data_rate' in settings_dict:
                new_val = float(settings_dict['data_rate'])
                if new_val < 0:
                    self.log.error('Data rate must be float value > 0.')
                else:
                    data_rate = new_val

            if 'trace_window_size' in settings_dict:
                new_val = float(settings_dict['trace_window_size'])
                if new_val < 0:
                    self.log.error('Trace window size must be float value > 0.')
                else:
                    # Round window to match data rate
                    data_points = int(round(new_val * data_rate))
                    new_val = data_points / data_rate
                    self._trace_window_size = new_val

            self._samples_per_frame = self.data_rate // self._max_frame_rate
            self._init_data_arrays()
            settings = self.all_settings
            self.sigSettingsChanged.emit(settings)
            if not restart:
                self.sigDataChanged.emit(*self.trace_data)
        if restart:
            self.start_reading()
        return settings

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

            if self._data_recording_active:
                self._record_start_time = dt.datetime.now()
                self._recorded_data = list()

            if self._lock_in.start_stream() < 0:
                self.log.error('Error while starting streaming device data acquisition.')
                self._stop_requested = True
                self._sigNextDataFrame.emit()
                return -1

            # self.log.info("trace started")
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
                # self.log.info("trace stopped")
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
                    if self._lock_in.stop_stream() < 0:
                        self.log.error(
                            'Error while trying to stop streaming device data acquisition.')
                    if self._data_recording_active:
                        self._save_recorded_data(to_file=True, save_figure=True)
                        self._recorded_data = list()
                    self._data_recording_active = False
                    self.module_state.unlock()
                    self.sigStatusChanged.emit(False, False)
                    return

                samples_to_read = max(
                    (self._lock_in.available_samples // 1) * 1,
                    self._samples_per_frame * 1)
                if samples_to_read < 1:
                    self._sigNextDataFrame.emit()
                    return

                # read the current counter values
                data = self._lock_in.read_data(number_of_samples=samples_to_read)
                if data.shape[1] != samples_to_read:
                    self.log.error('Reading data from streamer went wrong; '
                                   'killing the stream with next data frame.')
                    self._stop_requested = True
                    self._sigNextDataFrame.emit()
                    return

                # Process data
                self._process_trace_data(data)

                # Emit update signal
                self.sigDataChanged.emit(*self.trace_data)
                self._sigNextDataFrame.emit()
        return

    def _process_trace_data(self, data):
        """
        Processes raw data from the streaming device
        """

        # Append data to save if necessary
        if self._data_recording_active:
            self._recorded_data.append(data.copy())

        data = data[:, -self._trace_data.shape[1]:]
        new_samples = data.shape[1]

        # Roll data array to have a continuously running time trace
        self._trace_data = np.roll(self._trace_data, -new_samples, axis=1)

        # Insert new data
        self._trace_data[:, -new_samples:] = data
        return

    def _stop_reader_wait(self):
        """
        Stops the counter and waits until it actually has stopped.

        @param timeout: float, the max. time in seconds how long the method should wait for the
                        process to stop.

        @return: error code
        """
        with self.threadlock:
            self._stop_requested = True
            # terminate the hardware streaming
            if self._lock_in.stop_stream() < 0:
                self.log.error(
                    'Error while trying to stop streaming device data acquisition.')
            if self._data_recording_active:
                self._save_recorded_data(to_file=True, save_figure=True)
                self._recorded_data = list()
            self._data_recording_active = False
            self.module_state.unlock()
            self.sigStatusChanged.emit(False, False)
        return 0

    @QtCore.Slot()
    def start_recording(self):
        pass

    @QtCore.Slot()
    def stop_recording(self):
        pass

    @property
    def data_recording_active(self):
        return self._data_recording_active
