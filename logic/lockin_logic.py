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
from collections import OrderedDict

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

    # status vars with connection to lock-in GUI
    _trace_window_size = StatusVar('trace_window_size', default=6)
    _data_rate = StatusVar('data_rate', default=10)
    _pump_power_mW = StatusVar(default=1)
    _pump_wavelength_nm = StatusVar(default=532)
    _pump_spot_diameter_um = StatusVar(default=50)
    _probe_power_mW = StatusVar(default=1)
    _probe_wavelength_nm = StatusVar(default=532)
    _probe_spot_diameter_um = StatusVar(default=50)
    _laser_repetition_rate_kHz = StatusVar(default=1)
    _modulation_frequency_kHz = StatusVar(default=0.5)
    _measurements_type = StatusVar(default='REFLECTION')
    _arbitrary_tag = StatusVar(default='_arb_tag_')

    def __init__(self, *args, **kwargs):
        """
        """
        super().__init__(*args, **kwargs)

        self._lock_in = None
        self._delay = None
        self._save_logic = None

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
        self._save_logic = self.savelogic()

        # Flag to stop the loop and process variables
        self._stop_requested = True
        self._data_recording_active = False
        self._record_start_time = None

        self._samples_per_frame = self.data_rate // self._max_frame_rate

        self._sigNextDataFrame.connect(self.acquire_data_block, QtCore.Qt.QueuedConnection)

        # connecting external signal
        self._delay.sigGetMeasurePoint.connect(self.record_measurement_point)
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
        """Init dictionary of arrays for time-dependent measurements"""
        self.data_dict = dict({'delay_position (mm)': np.array([]),
                               'R (V)': np.array([]),
                               'X (V)': np.array([]),
                               'Y (V)': np.array([])
                               })
        self.data_dict_avg = dict({'delay_position (mm)': np.array([]),
                                   'R (V)': np.array([]),
                                   'X (V)': np.array([]),
                                   'Y (V)': np.array([])
                                   })
        # self.log.info('im clean')
        # TODO: this one is for fixed keys up to now, will be generalzied later

    @QtCore.Slot()
    def record_measurement_point(self):
        """Combines measurement data into an array and writes it to dictionary """
        current_position = self._delay._position_mm
        [x, y] = self._lock_in.getData()
        r = np.sqrt(x ** 2 + y ** 2)
        list_to_append = [current_position, r, x, y]
        dat_dict = self.data_dict
        for i, (k, v) in enumerate(dat_dict.items()):
            dat_dict[k] = np.hstack((dat_dict[k], list_to_append[i]))
        self.data_dict = dat_dict

        self.avg_signal_points(self.data_dict)  # calling this to update dict with avg values

    def avg_signal_points(self, raw_data_dict):
        """Performs averaging using the last few points with
         the same position on the delay line"""
        delays = raw_data_dict['delay_position (mm)']
        if len(delays) == 1:
            for k, v in self.data_dict_avg.items():
                self.data_dict_avg[k] = raw_data_dict[k]
            return 0
        if delays[-1] == delays[-2]:
            ind = np.unique(delays, return_index=True)[1][-1:]  # index for the last same elements
            for k, v in self.data_dict_avg.items():
                self.data_dict_avg[k][-1] = np.mean([raw_data_dict[k][ind[0]:]])
            # return data_dict_avg
        else:
            for k, v in self.data_dict_avg.items():
                self.data_dict_avg[k] = np.append(self.data_dict_avg[k], raw_data_dict[k][-1])
            # return data_dict_avg

    def save_data(self, name_tag='', custom_header=None):
        """
        :param string name_tag: postfix name tag for saved filename.
        :param OrderedDict custom_header:
        :return:
            This ordered dictionary is added to the default data file header. It allows arbitrary
            additional experimental information to be included in the saved data file header.
        """
        filepath = self._save_logic.get_path_for_module(module_name='spectroscopy')

        # TODO: introduce some real and additional parameters
        parameters = OrderedDict()
        parameters['Pump power (mW)'] = self._pump_power_mW
        parameters['Pump wavelength (nm)'] = self._pump_wavelength_nm
        parameters['Pump spot diameter (um)'] = self._pump_spot_diameter_um
        parameters['Probe power (mW)'] = self._probe_power_mW
        parameters['Probe wavelength (nm)'] = self._probe_wavelength_nm
        parameters['Probe spot diameter (um)'] = self._probe_spot_diameter_um
        parameters['Laser repetition rate (kHz)'] = self._laser_repetition_rate_kHz
        parameters['Modulation frequency (kHz)'] = self._modulation_frequency_kHz
        parameters['Arbitrary values'] = self._arbitrary_tag

        # add any custom header params
        if custom_header is not None:
            for key in custom_header:
                parameters[key] = custom_header[key]

        # self._proceed_data_dict.popitem('Pixels')
        data = self.data_dict

        # data = OrderedDict()

        # keys = ['delay_position (mm)', 'R (V)', 'X (V)', 'Y (V)']
        # dat_dic = dict(zip(keys, pro))

        # print(dat_dic)

        # data = OrderedDict()
        # x_axis_list = ['Pixels',
        #                'Wavelength (nm)',
        #                'Raman shift (cm-1)',
        #                'Energy (eV)',
        #                'Energy (meV)',
        #                'Wavenumber (cm-1)',
        #                'Frequency (THz)',
        #                "Energy RELATIVE (meV)",
        #                "Frequency RELATIVE (THz)"]
        # y_axis_list = ['Counts', 'Counts / s', 'Counts / (s * mW)']

        # generate a name_tag using various experimental parameters
        name_tag = ''
        if self._measurements_type == 'REFLECTION':
            name_tag += 'REF_'
        elif self._measurements_type == 'BALANCE':
            name_tag += 'BAL_'
        else:
            pass
        name_tag += 'pmp_pwr_' + str(self._pump_power_mW) + '_mW_'
        # name_tag += 'pump_' + str(self._pump_wavelength_nm) + '_nm_'
        # name_tag += 'probe_' + str(self._probe_wavelength_nm) + '_nm_'
        name_tag += str(self._arbitrary_tag)
        name_tag.replace('.', 'p')

        # Add name_tag as postfix to filename
        # if name_tag != '':
        #     filelabel = filelabel + '_' + name_tag

        self._save_logic.save_data(data,
                                   filepath=filepath,
                                   parameters=parameters,
                                   filelabel=name_tag
                                   )
        self.log.debug('Spectrum saved to:\n{0}'.format(filepath))

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
