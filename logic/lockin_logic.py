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

    data = []

    # declare signals
    sigDataChanged = QtCore.Signal(object, object, object, object)
    sigStatusChanged = QtCore.Signal(bool, bool)
    sigSettingsChanged = QtCore.Signal(dict)
    _sigNextDataFrame = QtCore.Signal()  # internal signal

    # pseudo config options
    _max_frame_rate = 10
    _calc_digital_freq = True

    # status vars
    _trace_window_size = StatusVar('trace_window_size', default=6)
    _moving_average_width = StatusVar('moving_average_width', default=9)

    def __init__(self, *args, **kwargs):
        """
        """
        super().__init__(*args, **kwargs)

        self._lock_in = None

        # locking for thread safety
        self.threadlock = Mutex()
        self._samples_per_frame = None
        self._stop_requested = True

        # Data arrays
        self._trace_data = None
        self._trace_times = None
        self._trace_data_averaged = None
        self.__moving_filter = None

        # for data recording
        self._recorded_data = None
        self._data_recording_active = False
        self._record_start_time = None

        self._oversampling_factor = 1

        return

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._lock_in = self.lock_in()

        # Flag to stop the loop and process variables
        self._stop_requested = True
        self._data_recording_active = False
        self._record_start_time = None

        self._samples_per_frame = self.data_rate // self._max_frame_rate

        self._sigNextDataFrame.connect(self.acquire_data_block, QtCore.Qt.QueuedConnection)

        settings = self.all_settings
        self.configure_settings(**settings)

    def on_deactivate(self):
        """
        Deinitialisation performed during deactivation of the module.
        """
        if self.module_state() == 'locked':
            self._stop_reader_wait()

        self._sigNextDataFrame.disconnect()

        self._data_rate = self.data_rate

        return

    @property
    def all_settings(self):
        return {'oversampling_factor': 1,
                # 'active_channels': 1,
                # 'averaged_channels': 0,
                'moving_average_width': self.moving_average_width,
                'trace_window_size': self.trace_window_size,
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
    def moving_average_width(self):
        return self._moving_average_width

    @property
    def data_rate(self):
        return self.sampling_rate

    @property
    def sampling_rate(self):
        return self._lock_in.sample_rate

    @property
    def data_recording_active(self):
        return self._data_recording_active

    @property
    def trace_data(self):
        # OLD
        # data_offset = self._trace_data.shape[1]
        # data = {'ch1': self._trace_data}
        data = {ch: self._trace_data[i] for i, ch in
                enumerate(['X', 'Y'])}
        return self._trace_times, data

    @property
    def averaged_trace_data(self):
        # data_offset = self._trace_data.shape[1] - self._moving_average_width // 2
        data = {'ch1': self._trace_data}
        return self._trace_times, data

    # def get_data(self):
        # return self._lock_in.getData()
    # below is direct copypaste from other sources

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
            # all_ch = tuple(ch.name for ch in self._streamer.available_channels)
            data_rate = self.data_rate
            # active_ch = self.active_channel_names

            if 'moving_average_width' in settings_dict:
                new_val = int(settings_dict['moving_average_width'])
                if new_val < 1:
                    self.log.error('Moving average width must be integer value >= 1 '
                                   '(received: {0:d}).'.format(new_val))
                elif new_val % 2 == 0:
                    new_val += 1
                    self.log.warning('Moving average window must be odd integer number in order to '
                                     'ensure perfect data alignment. Will increase value to {0:d}.'
                                     ''.format(new_val))
                if new_val / data_rate > self.trace_window_size:
                    if 'data_rate' in settings_dict or 'trace_window_size' in settings_dict:
                        self._moving_average_width = new_val
                        self.__moving_filter = np.full(shape=self.moving_average_width,
                                                       fill_value=1.0 / self.moving_average_width)
                    else:
                        self.log.warning('Moving average width to set ({0:d}) is smaller than the '
                                         'trace window size. Will adjust trace window size to '
                                         'match.'.format(new_val))
                        self._trace_window_size = float(new_val / data_rate)
                else:
                    self._moving_average_width = new_val
                    self.__moving_filter = np.full(shape=self.moving_average_width,
                                                   fill_value=1.0 / self.moving_average_width)

            if 'data_rate' in settings_dict:
                new_val = float(settings_dict['data_rate'])
                if new_val < 0:
                    self.log.error('Data rate must be float value > 0.')
                # else:
                #     if self.has_active_analog_channels and self.has_active_digital_channels:
                #         min_val = constraints.combined_sample_rate.min
                #         max_val = constraints.combined_sample_rate.max
                #     elif self.has_active_analog_channels:
                #         min_val = constraints.analog_sample_rate.min
                #         max_val = constraints.analog_sample_rate.max
                #     else:
                #         min_val = constraints.digital_sample_rate.min
                #         max_val = constraints.digital_sample_rate.max
                #     sample_rate = new_val * self.oversampling_factor
                #     if not (min_val <= sample_rate <= max_val):
                #         self.log.warning('Data rate to set ({0:.3e}Hz) would cause sampling rate '
                #                          'outside allowed value range. Will clip data rate to '
                #                          'boundaries.'.format(new_val))
                #         if sample_rate > max_val:
                #             new_val = max_val / self.oversampling_factor
                #         elif sample_rate < min_val:
                #             new_val = min_val / self.oversampling_factor

                    data_rate = new_val
                    if self.moving_average_width / data_rate > self.trace_window_size:
                        if 'trace_window_size' not in settings_dict:
                            self.log.warning('Data rate to set ({0:.3e}Hz) would cause too few '
                                             'data points within the trace window. Adjusting window'
                                             ' size.'.format(new_val))
                            self._trace_window_size = self.moving_average_width / data_rate

            if 'trace_window_size' in settings_dict:
                new_val = float(settings_dict['trace_window_size'])
                if new_val < 0:
                    self.log.error('Trace window size must be float value > 0.')
                else:
                    # Round window to match data rate
                    data_points = int(round(new_val * data_rate))
                    new_val = data_points / data_rate
                    # Check if enough points are present
                    if data_points < self.moving_average_width:
                        self.log.warning('Requested trace_window_size ({0:.3e}s) would have too '
                                         'few points for moving average. Adjusting window size.'
                                         ''.format(new_val))
                        new_val = self.moving_average_width / data_rate
                    self._trace_window_size = new_val

            if 'active_channels' in settings_dict:
                new_val = tuple(settings_dict['active_channels'])
                if any(ch not in all_ch for ch in new_val):
                    self.log.error('Invalid channel found to set active.')
                else:
                    active_ch = new_val

            if 'averaged_channels' in settings_dict:
                new_val = tuple(ch for ch in settings_dict['averaged_channels'] if ch in active_ch)
                if any(ch not in all_ch for ch in new_val):
                    self.log.error('Invalid channel found to set activate moving average for.')
                else:
                    self._averaged_channels = new_val

            # # Apply settings to hardware if needed
            # self._streamer.configure(sample_rate=data_rate * self.oversampling_factor,
            #                          streaming_mode=StreamingMode.CONTINUOUS,
            #                          active_channels=active_ch,
            #                          buffer_size=10000000,
            #                          use_circular_buffer=True)

            # update actually set values
            # self._averaged_channels = tuple(
            #     ch for ch in self._averaged_channels if ch in self.active_channel_names)

            self._samples_per_frame = self.data_rate // self._max_frame_rate
            self._init_data_arrays()
            settings = self.all_settings
            self.sigSettingsChanged.emit(settings)
            if not restart:
                self.sigDataChanged.emit(*self.trace_data, *self.averaged_trace_data)
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
                self.sigDataChanged.emit(*self.trace_data, *self.averaged_trace_data)
                self._sigNextDataFrame.emit()
        return

    def _process_trace_data(self, data):
        """
        Processes raw data from the streaming device
        """
        # Down-sample and average according to oversampling factor

        # digital_channels = [c for c, typ in self.active_channel_types.items() if
        #                     typ == StreamChannelType.DIGITAL]
        # # Convert digital event count numbers into frequencies according to ConfigOption
        # if self._calc_digital_freq and digital_channels:
        #     data[:len(digital_channels)] *= self.sampling_rate

        # Append data to save if necessary
        if self._data_recording_active:
            self._recorded_data.append(data.copy())

        data = data[:, -self._trace_data.shape[1]:]
        new_samples = data.shape[1]

        # Roll data array to have a continuously running time trace
        self._trace_data = np.roll(self._trace_data, -new_samples, axis=1)
        # Insert new data
        self._trace_data[:, -new_samples:] = data

        # # Calculate moving average by using numpy.convolve with a normalized uniform filter
        # if self.moving_average_width > 1 and self.averaged_channel_names:
        #     # Only convolve the new data and roll the previously calculated moving average
        #     self._trace_data_averaged = np.roll(self._trace_data_averaged, -new_samples, axis=1)
        #     offset = new_samples + len(self.__moving_filter) - 1
        #     for i, ch in enumerate(self.averaged_channel_names):
        #         data_index = self.active_channel_names.index(ch)
        #         self._trace_data_averaged[i, -new_samples:] = np.convolve(
        #             self._trace_data[data_index, -offset:], self.__moving_filter, mode='valid')
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
            if self._streamer.stop_stream() < 0:
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
