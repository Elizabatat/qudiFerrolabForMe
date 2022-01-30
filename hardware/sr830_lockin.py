# -*- coding: utf-8 -*-

"""
This file contains the hardware control of the SR830 lock-in amplifier by STANDFORD RESEARCH.
Only RS232 communication is realized with control through SCPI instructions.

It is done with pseudo 2 channels being read X and Y

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

import visa
import time
import numpy as np

from core.module import Base
from core.configoption import ConfigOption
from core.util.helpers import natural_sort

from interface.simple_data_interface import SimpleDataInterface


# TODO: all interactions are use query to remove echo and first symbol stripped to remove /n char

class sr830LockIn(Base, SimpleDataInterface):
    """
    Main class for lock-in control.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Internal settings
        self.__sample_rate = -1.0
        self.__data_type = np.float64
        self.__stream_length = -1
        self.__buffer_size = -1

        # Buffer things
        self._data_buffer = np.empty(0, dtype=self.__data_type)
        self._has_overflown = False
        self._is_running = False
        self._last_read = None
        self._start_time = None
        return

    _modclass = 'sr830'
    _modtype = 'hardware'

    _com_port_lock_in = ConfigOption('com_port_lock_in', 'ASRL5::INSTR', missing='warn')

    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        """

        self.rm = visa.ResourceManager()
        try:
            self._lock_in_handle = self.rm.open_resource(self._com_port_lock_in,
                                                         baud_rate=9600,
                                                         parity=0,
                                                         write_termination='\r',
                                                         read_termination='\r'
                                                         )
            time.sleep(0.1)
            self.log.info("All good, lock-in is connected!")

            self.__sample_rate = 10  # Hz
            self.__data_type = np.float64
            self.__stream_length = 0
            self.__buffer_size = 10000

            # Reset data buffer
            self._data_buffer = np.empty(0, dtype=self.__data_type)
            self._has_overflown = False
            self._is_running = False
            self._last_read = None
            self._start_time = None

        except:
            self.log.warning('Cannot connect to lock-in! Check ports.')

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # Buffer things
        self._has_overflown = False
        self._is_running = False
        self._last_read = None
        # Free memory if possible while module is inactive
        self._data_buffer = np.empty(0, dtype=self.__data_type)

        self._lock_in_handle.close()

        return

    def getData(self):
        """ Returns X and Y from the first channel as an array of floats. """
        _data = self._lock_in_handle.query("snap?1,2")
        return list(map(float, _data.split(',')))

    def getChannels(self):
        pass

    # copypaste from dummy streamer below

    @property
    def is_running(self):
        """
        Read-only flag indicating if the data acquisition is running.

        @return bool: Data acquisition is running (True) or not (False)
        """
        return self._is_running

    def _init_buffer(self):
        if not self.is_running:
            self._data_buffer = np.zeros(self.buffer_size)
            self._has_overflown = False
        return

    @property
    def buffer_overflown(self):
        """
        Read-only flag to check if the read buffer has overflown.
        In case of a circular buffer it indicates data loss.
        In case of a non-circular buffer the data acquisition should have stopped if this flag is
        coming up.
        Flag will only be reset after starting a new data acquisition.

        @return bool: Flag indicates if buffer has overflown (True) or not (False)
        """
        return self._has_overflown

    @property
    def available_samples(self):
        """
        Read-only property to return the currently available number of samples per channel ready
        to read from buffer.

        @return int: Number of available samples per channel
        """
        if not self.is_running:
            return 0
        return int((time.perf_counter() - self._last_read) * self.__sample_rate)

    @property
    def buffer_size(self):
        """
        Read-only property to return the currently buffer size.
        Buffer size corresponds to the number of samples per channel that can be buffered. So the
        actual buffer size in bytes can be estimated by:
            buffer_size * number_of_channels * size_in_bytes(data_type)

        @return int: current buffer size in samples per channel
        """
        return self.__buffer_size

    @buffer_size.setter
    def buffer_size(self, size):
        # if self._check_settings_change():
        #     size = int(size)
        #     if size < 1:
        #         self.log.error('Buffer size smaller than 1 makes no sense. Tried to set {0} as '
        #                        'buffer size and failed.'.format(size))
        #         return
        self.__buffer_size = int(size)
        self._init_buffer()
        return

    @property
    def sample_rate(self):
        """
        Read-only property to return the currently set sample rate

        @return float: current sample rate in Hz
        """
        return self.__sample_rate

    @sample_rate.setter
    def sample_rate(self, rate):
        self.__sample_rate = float(rate)
        return

    def start_stream(self):
        """
        Start the data acquisition and data stream.

        @return int: error code (0: OK, -1: Error)
        """
        if self.is_running:
            self.log.warning('Unable to start input stream. It is already running.')
            return 0

        self._init_buffer()
        self._is_running = True
        self._start_time = time.perf_counter()
        self._last_read = self._start_time
        return 0

    def stop_stream(self):
        """
        Stop the data acquisition and data stream.

        @return int: error code (0: OK, -1: Error)
        """
        if self.is_running:
            self._is_running = False
        return 0

    def read_data_into_buffer(self, buffer, number_of_samples=None):
        """
        Read data from the stream buffer into a 1D/2D numpy array given as parameter.
        In case of a single data channel the numpy array can be either 1D or 2D. In case of more
        channels the array must be 2D with the first index corresponding to the channel number and
        the second index serving as sample index:
            buffer.shape == (self.number_of_channels, number_of_samples)
        The numpy array must have the same data type as self.data_type.
        If number_of_samples is omitted it will be derived from buffer.shape[1]

        This method will not return until all requested samples have been read or a timeout occurs.

        @param numpy.ndarray buffer: The numpy array to write the samples to
        @param int number_of_samples: optional, number of samples to read per channel. If omitted,
                                      this number will be derived from buffer axis 1 size.

        @return int: Number of samples read into buffer; negative value indicates error
                     (e.g. read timeout)
        """
        if not self.is_running:
            self.log.error('Unable to read data. Device is not running.')
            return -1

        if not isinstance(buffer, np.ndarray) or buffer.dtype != self.__data_type:
            self.log.error('buffer must be numpy.ndarray with dtype {0}. Read failed.'
                           ''.format(self.__data_type))
            return -1

        if buffer.ndim == 2:
            if buffer.shape[0] != self.number_of_channels:
                self.log.error('Configured number of channels ({0:d}) does not match first '
                               'dimension of 2D buffer array ({1:d}).'
                               ''.format(self.number_of_channels, buffer.shape[0]))
                return -1
            number_of_samples = buffer.shape[1] if number_of_samples is None else number_of_samples
            buffer = buffer.flatten()
        elif buffer.ndim == 1:
            number_of_samples = (buffer.size // 1) if number_of_samples is None else number_of_samples
        else:
            self.log.error('Buffer must be a 1D or 2D numpy.ndarray.')
            return -1

        if number_of_samples < 1:
            return 0
        while self.available_samples < number_of_samples:
            time.sleep(0.001)

        # Check for buffer overflow
        avail_samples = self.available_samples
        if avail_samples > self.buffer_size:
            self._has_overflown = True

        # offset = 0
        # analog_x = np.arange(number_of_samples, dtype=self.__data_type) / self.__sample_rate
        # analog_x *= 2 * np.pi
        # analog_x += 2 * np.pi * (self._last_read - self._start_time)
        # self._last_read = time.perf_counter()
        #
        # amplitude = 10
        # np.sin(analog_x, out=buffer[offset:(offset+number_of_samples)])
        # buffer[offset:(offset + number_of_samples)] *= amplitude
        # noise_level = 0.1 * amplitude
        # noise = noise_level - 2 * noise_level * np.random.rand(number_of_samples)
        # buffer[offset:(offset + number_of_samples)] += noise
        # offset += number_of_samples

        # offset = 0
        # buffer[offset:number_of_samples] = self.getData()[0]
        # offset += number_of_samples
        # buffer[offset:(offset+number_of_samples)] = self.getData()[1]
        # offset += number_of_samples

        # buffer[offset:(offset + number_of_samples)] += self.getData()[1]
        # offset += number_of_samples
        # for i in range(2):
        #     buffer[offset:(offset + number_of_samples)] += self.getData()[0]
        #     offset += number_of_samples

        # worked best:
        self._last_read = time.perf_counter()
        buffer[0:number_of_samples] = self.getData()[0]
        buffer[1:number_of_samples+1] = self.getData()[1]
        return number_of_samples

    def read_data(self, number_of_samples=None):
        """
        Read data from the stream buffer into a 2D numpy array and return it.
        The arrays first index corresponds to the channel number and the second index serves as
        sample index:
            return_array.shape == (self.number_of_channels, number_of_samples)
        The numpy arrays data type is the one defined in self.data_type.
        If number_of_samples is omitted all currently available samples are read from buffer.

        This method will not return until all requested samples have been read or a timeout occurs.

        @param int number_of_samples: optional, number of samples to read per channel. If omitted,
                                      all available samples are read from buffer.

        @return numpy.ndarray: The read samples
        """

        if not self.is_running:
            self.log.error('Unable to read data. Device is not running.')
            return np.empty((0, 0), dtype=self.data_type)

        if number_of_samples is None:
            read_samples = self.read_available_data_into_buffer(self._data_buffer)
            if read_samples < 0:
                return np.empty((0, 0), dtype=self.data_type)
        else:
            read_samples = self.read_data_into_buffer(self._data_buffer,
                                                      number_of_samples=number_of_samples)
            if read_samples != number_of_samples:
                return np.empty((0, 0), dtype=self.data_type)

        total_samples = 2 * read_samples
        return self._data_buffer[:total_samples].reshape((2,
                                                          number_of_samples))

    def read_single_point(self):
        """
        This method will initiate a single sample read on each configured data channel.
        In general this sample may not be acquired simultaneous for all channels and timing in
        general can not be assured. Us this method if you want to have a non-timing-critical
        snapshot of your current data channel input.
        May not be available for all devices.
        The returned 1D numpy array will contain one sample for each channel.

        @return numpy.ndarray: 1D array containing one sample for each channel. Empty array
                               indicates error.
        """
        # if not self.is_running:
        #     self.log.error('Unable to read data. Device is not running.')
        #     return np.empty(0, dtype=self.__data_type)

        # data = np.empty(1, dtype=self.__data_type)
        # amplitude = 10
        # analog_x = 2 * np.pi
        # noise_level = 0.05 * amplitude
        # noise = noise_level - 2 * noise_level * np.random.rand()
        # data = amplitude * np.sin(analog_x) + noise

        data = self.getData()[0]
        #
        # self._last_read = time.perf_counter()
        # for i, chnl in enumerate(self.__active_channels):
        #     if chnl in self._digital_channels:
        #         ch_index = self._digital_channels.index(chnl)
        #         events_per_bin = self._digital_event_rates[ch_index] / self.__sample_rate
        #         data[i] = np.random.poisson(events_per_bin)
        #     else:
        #         ch_index = self._analog_channels.index(chnl)
        #         amplitude = self._analog_amplitudes[ch_index]
        #         noise_level = 0.05 * amplitude
        #         noise = noise_level - 2 * noise_level * np.random.rand()
        #         data[i] = amplitude * np.sin(analog_x) + noise
        return data
