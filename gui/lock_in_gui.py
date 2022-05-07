# -*- coding: utf-8 -*-
"""
This file contains a gui to communicate with lock-ins, like SR830.

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
import sys

from core.module import Connector
from core.configoption import ConfigOption
from gui.guibase import GUIBase
from gui.colordefs import QudiPalettePale as palette
from qtpy import QtWidgets
from qtpy import QtCore
from qtpy import uic


class LockInMainWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'lock_in_gui.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class LockInGui(GUIBase):
    """ FIXME: Please document
    """
    _modclass = 'lockingui'
    _modtype = 'gui'

    # declare connectors
    lockinlogic = Connector(interface='GenericLogic')

    _use_antialias = ConfigOption('use_antialias', default=True)

    sigStartCounter = QtCore.Signal()
    sigStopCounter = QtCore.Signal()
    # sigStartRecording = QtCore.Signal()
    # sigStopRecording = QtCore.Signal()
    sigSettingsChanged = QtCore.Signal(dict)

    _data = []

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.log.debug('The following configuration was found.')

        self._time_series_logic = None

        self._mw = None

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

    def test_signal(self):
        self.log.info("test")

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """
        self._lock_in_logic = self.lockinlogic()

        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = LockInMainWindow()

        # Setup dock widgets
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)

        # Trace spectrum (adjustment regime to continuously read lock-in)
        self._trw = self._mw.trace_PlotWidget  # pg.PlotWidget(name='Counter1')
        self._trace_spectrum = self._trw.plotItem

        self._curve1 = self._trw.plot()
        self._curve1.setPen(palette.c1,
                            width=1,
                            clipToView=True,
                            downsampleMethod='subsample',
                            autoDownsample=True,
                            antialias=False)

        self._curve2 = self._trw.plot()
        self._curve2.setPen(palette.c2,
                            width=1,
                            clipToView=True,
                            downsampleMethod='subsample',
                            autoDownsample=True,
                            antialias=False)

        self._trace_spectrum.showAxis('top')
        self._trace_spectrum.showAxis('right')

        self._trace_spectrum.setLabel('bottom', 'Time', units='s')
        self._trace_spectrum.setLabel('left', 'Intensity (arb. units.)')

        # R channel spectrum
        self._rrw = self._mw.r_PlotWidget
        self._r_spectrum = self._rrw.plotItem

        self._curve_r = self._rrw.plot(pen=None, symbol='o', symbolPen=palette.c1, symbolBrush=None, symbolSize=7)
        self._curve_r.setAlpha(0.5, False)

        self._curve_r_avg = self._rrw.plot()  # Draw lines for averaged one
        self._curve_r_avg.setPen(palette.c1,
                                 width=3,
                                 antialias=False)

        self._r_spectrum.showAxis('top')
        self._r_spectrum.showAxis('right')

        self._r_spectrum.setLabel('bottom', 'Delay line position', units='mm')
        self._r_spectrum.setLabel('left', 'R (X^2 + Y^2)', units='V')

        # X channel spectrum
        self._xrw = self._mw.x_PlotWidget
        self._x_spectrum = self._xrw.plotItem

        self._curve_x = self._xrw.plot(pen=None, symbol='o', symbolPen=palette.c2, symbolBrush=None, symbolSize=7)
        self._curve_x.setAlpha(0.5, False)

        self._curve_x_avg = self._xrw.plot()
        self._curve_x_avg.setPen(palette.c2,
                                 width=3,
                                 antialias=False)

        self._x_spectrum.showAxis('top')
        self._x_spectrum.showAxis('right')

        self._x_spectrum.setLabel('bottom', 'Delay line position', units='mm')
        self._x_spectrum.setLabel('left', 'X lock-in channel', units='V')

        # Y channel spectrum
        self._yrw = self._mw.y_PlotWidget
        self._y_spectrum = self._yrw.plotItem

        self._curve_y = self._yrw.plot(pen=None, symbol='o', symbolPen=palette.c3, symbolBrush=None, symbolSize=7)
        self._curve_y.setAlpha(0.5, False)

        self._curve_y_avg = self._yrw.plot()
        self._curve_y_avg.setPen(palette.c3,
                                 width=3,
                                 antialias=False)

        self._y_spectrum.showAxis('top')
        self._y_spectrum.showAxis('right')

        self._y_spectrum.setLabel('bottom', 'Delay line position', units='mm')
        self._y_spectrum.setLabel('left', 'Y lock-in channel', units='V')

        #####################
        # Setting default parameters
        self.update_status()
        self.update_settings()
        self.update_data()

        # load spinBoxes states
        self._mw.pump_power_DoubleSpinBox.setValue(self._lock_in_logic._pump_power_mW)
        self._mw.pump_wavelength_DoubleSpinBox.setValue(self._lock_in_logic._pump_wavelength_nm)
        self._mw.pump_spot_diameter_DoubleSpinBox.setValue(self._lock_in_logic._pump_spot_diameter_um)
        self._mw.probe_power_DoubleSpinBox.setValue(self._lock_in_logic._probe_power_mW)
        self._mw.probe_wavelength_DoubleSpinBox.setValue(self._lock_in_logic._probe_wavelength_nm)
        self._mw.probe_spot_diameter_DoubleSpinBox.setValue(self._lock_in_logic._probe_spot_diameter_um)
        self._mw.laser_repetition_rate_DoubleSpinBox.setValue(self._lock_in_logic._laser_repetition_rate_kHz)
        self._mw.modulation_frequency_DoubleSpinBox.setValue(self._lock_in_logic._modulation_frequency_kHz)
        self._mw.arbitrary_tag_lineEdit.setText(self._lock_in_logic._arbitrary_tag)

        #####################
        # Connecting user interactions
        # Actions
        self._mw.start_trace_Action.triggered.connect(self.start_clicked)
        self._mw.save_data_Action.triggered.connect(self.save_clicked)

        # connect Boxes
        self._mw.trace_window_DoubleSpinBox.editingFinished.connect(self.data_window_changed)
        self._mw.data_rate_DoubleSpinBox.editingFinished.connect(self.data_rate_changed)
        self._mw.pump_power_DoubleSpinBox.editingFinished.connect(self.pump_power_changed)
        self._mw.pump_wavelength_DoubleSpinBox.editingFinished.connect(self.pump_wavelength_changed)
        self._mw.pump_spot_diameter_DoubleSpinBox.editingFinished.connect(self.pump_spot_diameter_changed)
        self._mw.probe_power_DoubleSpinBox.editingFinished.connect(self.probe_power_changed)
        self._mw.probe_wavelength_DoubleSpinBox.editingFinished.connect(self.probe_wavelength_changed)
        self._mw.probe_spot_diameter_DoubleSpinBox.editingFinished.connect(self.probe_spot_diameter_changed)
        self._mw.laser_repetition_rate_DoubleSpinBox.editingFinished.connect(self.laser_repetition_rate_changed)
        self._mw.modulation_frequency_DoubleSpinBox.editingFinished.connect(self.modulation_frequency_changed)
        self._mw.arbitrary_tag_lineEdit.editingFinished.connect(self.arbitrary_tag_changed)

        ###################
        # Starting the physical measurements

        self.sigStartCounter.connect(
            self._lock_in_logic.start_reading, QtCore.Qt.QueuedConnection)
        self.sigStopCounter.connect(
            self._lock_in_logic.stop_reading, QtCore.Qt.QueuedConnection)
        # self.sigStartRecording.connect(
        #     self._lock_in_logic.start_recording, QtCore.Qt.QueuedConnection)
        # self.sigStopRecording.connect(
        #     self._lock_in_logic.stop_recording, QtCore.Qt.QueuedConnection)
        self.sigSettingsChanged.connect(
            self._lock_in_logic.configure_settings, QtCore.Qt.QueuedConnection)

        # Signals from logic
        self._lock_in_logic.sigDataChanged.connect(
            self.update_data, QtCore.Qt.QueuedConnection)
        self._lock_in_logic.sigSettingsChanged.connect(
            self.update_settings, QtCore.Qt.QueuedConnection)
        self._lock_in_logic.sigStatusChanged.connect(
            self.update_status, QtCore.Qt.QueuedConnection)
        self._lock_in_logic._delay.sigGetMeasurePoint.connect(
            self.update_x_y, QtCore.Qt.QueuedConnection)

    def show(self):
        """ Make window visible and put it above all other windows """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def on_deactivate(self):
        """ Deactivate the module properly """
        # FIXME: !

        # disconnect local GUI signals
        self.sigStartCounter.disconnect()
        self.sigStopCounter.disconnect()
        # self.sigStartRecording.disconnect()
        # self.sigStopRecording.disconnect()
        self.sigSettingsChanged.disconnect()

        # disconnect signals from logic
        self._lock_in_logic.sigDataChanged.disconnect()
        self._lock_in_logic.sigSettingsChanged.disconnect()
        self._lock_in_logic.sigStatusChanged.disconnect()

        # disconnect spinBoxes
        self._mw.data_rate_DoubleSpinBox.editingFinished.disconnect()
        self._mw.trace_window_DoubleSpinBox.editingFinished.disconnect()
        self._mw.pump_power_DoubleSpinBox.editingFinished.disconnect()
        self._mw.pump_wavelength_DoubleSpinBox.editingFinished.disconnect()
        self._mw.pump_spot_diameter_DoubleSpinBox.editingFinished.disconnect()
        self._mw.probe_power_DoubleSpinBox.editingFinished.disconnect()
        self._mw.probe_wavelength_DoubleSpinBox.editingFinished.disconnect()
        self._mw.probe_spot_diameter_DoubleSpinBox.editingFinished.disconnect()
        self._mw.laser_repetition_rate_DoubleSpinBox.editingFinished.disconnect()
        self._mw.modulation_frequency_DoubleSpinBox.editingFinished.disconnect()
        self._mw.arbitrary_tag_lineEdit.editingFinished.disconnect()

        self._mw.close()

    @QtCore.Slot()
    @QtCore.Slot(bool, bool)
    def update_status(self, running=None, recording=None):
        """
        Function to ensure that the GUI displays the current measurement status

        @param bool running: True if the data trace streaming is running
        @param bool recording: True if the data trace recording is active        """

        if running is None:
            running = self._lock_in_logic.module_state() == 'locked'
        # if recording is None:
        #     recording = self._l/ock_in_logic.data_recording_active

        self._mw.start_trace_Action.setChecked(running)
        self._mw.start_trace_Action.setText('Stop trace' if running else 'Start trace')

        # self._mw.record_trace_Action.setChecked(recording)
        # self._mw.record_trace_Action.setText('Save recorded' if recording else 'Start recording')

        self._mw.start_trace_Action.setEnabled(True)
        # self._mw.record_trace_Action.setEnabled(running)

        self._mw.data_rate_DoubleSpinBox.setEnabled(not running)
        self._mw.trace_window_DoubleSpinBox.setEnabled(not running)
        self._mw.pump_power_DoubleSpinBox.setEnabled(not running)

    @QtCore.Slot()
    def data_window_changed(self):
        """ Handling the change of the trance window and sending it to the measurement.
        """
        val = self._mw.trace_window_DoubleSpinBox.value()
        self.sigSettingsChanged.emit({'trace_window_size': val})

    @QtCore.Slot()
    def data_rate_changed(self):
        """ Handling the change of the data rate (points per s, Hz) and sending it to the measurement.
        """
        val = self._mw.data_rate_DoubleSpinBox.value()
        self.sigSettingsChanged.emit({'data_rate': val})

    def pump_power_changed(self):
        self._lock_in_logic._pump_power_mW = self._mw.pump_power_DoubleSpinBox.value()

    def pump_wavelength_changed(self):
        self._lock_in_logic._pump_wavelength_nm = self._mw.pump_wavelength_DoubleSpinBox.value()

    def pump_spot_diameter_changed(self):
        self._lock_in_logic._pump_spot_diameter_um = self._mw.pump_spot_diameter_DoubleSpinBox.value()

    def probe_power_changed(self):
        self._lock_in_logic._probe_power_mW = self._mw.probe_power_DoubleSpinBox.value()

    def probe_wavelength_changed(self):
        self._lock_in_logic._probe_wavelength_nm = self._mw.probe_wavelength_DoubleSpinBox.value()

    def probe_spot_diameter_changed(self):
        self._lock_in_logic._probe_spot_diameter_um = self._mw.probe_spot_diameter_DoubleSpinBox.value()

    def laser_repetition_rate_changed(self):
        self._lock_in_logic._laser_repetition_rate_kHz = self._mw.laser_repetition_rate_DoubleSpinBox.value()

    def modulation_frequency_changed(self):
        self._lock_in_logic._modulation_frequency_kHz = self._mw.modulation_frequency_DoubleSpinBox.value()

    def arbitrary_tag_changed(self):
        self._lock_in_logic._arbitrary_tag = self._mw.arbitrary_tag_lineEdit.text()

    @QtCore.Slot()
    @QtCore.Slot(dict)
    def update_settings(self, settings_dict=None):
        if settings_dict is None:
            settings_dict = self._lock_in_logic.all_settings

        if 'trace_window_size' in settings_dict:
            self._mw.trace_window_DoubleSpinBox.blockSignals(True)
            self._mw.trace_window_DoubleSpinBox.setValue(settings_dict['trace_window_size'])
            self._mw.trace_window_DoubleSpinBox.blockSignals(False)
        if 'data_rate' in settings_dict:
            self._mw.data_rate_DoubleSpinBox.blockSignals(True)
            self._mw.data_rate_DoubleSpinBox.setValue(settings_dict['data_rate'])
            self._mw.data_rate_DoubleSpinBox.blockSignals(False)
        # if 'pump_power_mW' in settings_dict:
        #     self._mw.pump_power_DoubleSpinBox.blockSignals(True)
        #     self._mw.pump_power_DoubleSpinBox.setValue(settings_dict['pump_power_mW'])
        #     self._mw.pump_power_DoubleSpinBox.blockSignals(False)

        # self.apply_channel_settings(update_logic=False)
        return

    @QtCore.Slot()
    def start_clicked(self):
        """
        Handling the Start button to stop and restart the counter.
        """
        self._mw.start_trace_Action.setEnabled(False)
        # self._mw.record_trace_Action.setEnabled(False)

        self._mw.trace_window_DoubleSpinBox.setEnabled(False)
        self._mw.data_rate_DoubleSpinBox.setEnabled(False)
        self._mw.pump_power_DoubleSpinBox.setEnabled(False)

        if self._mw.start_trace_Action.isChecked():
            # TODO: get some settings from
            settings = {'trace_window_size': self._mw.trace_window_DoubleSpinBox.value(),
                        'data_rate': self._mw.data_rate_DoubleSpinBox.value(),
                        'pump_power_mW': self._mw.pump_power_DoubleSpinBox.value()
                        }
            self.sigSettingsChanged.emit(settings)
            self.sigStartCounter.emit()
        else:
            self.sigStopCounter.emit()
        pass

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        self._lock_in_logic.save_data()

    @QtCore.Slot()
    @QtCore.Slot(object, object)
    @QtCore.Slot(object, object, object, object)
    def update_data(self, data_time=None, data=None, smooth_time=None, smooth_data=None):
        """ The function that grabs the data and sends it to the plot.
        """
        if data_time is None and data is None:
            data_time, data = self._lock_in_logic.trace_data
            # smooth_time, smooth_data = self._lock_in_logic.averaged_trace_data
        elif (data_time is None) ^ (data is None):
            self.log.error('Must provide a full data set of x and y values. update_data failed.')
            return

        if data is not None:
            self._curve1.setData(y=data.get('X'), x=data_time)
            self._curve2.setData(y=data.get('Y'), x=data_time)

        return 0

    @QtCore.Slot()
    def update_x_y(self):
        """
        Kinda same as above but for point-by point measurements.
        At some point should be merged with trace update, probably.
        """
        self._curve_r.setData(
            x=self._lock_in_logic.data_dict['delay_position (mm)'],
            y=self._lock_in_logic.data_dict['R (V)']
        )
        self._curve_r_avg.setData(
            x=self._lock_in_logic.data_dict_avg['delay_position (mm)'],
            y=self._lock_in_logic.data_dict_avg['R (V)']
        )

        self._curve_x.setData(
            x=self._lock_in_logic.data_dict['delay_position (mm)'],
            y=self._lock_in_logic.data_dict['X (V)']
        )
        self._curve_x_avg.setData(
            x=self._lock_in_logic.data_dict_avg['delay_position (mm)'],
            y=self._lock_in_logic.data_dict_avg['X (V)']
        )

        self._curve_y.setData(
            x=self._lock_in_logic.data_dict['delay_position (mm)'],
            y=self._lock_in_logic.data_dict['Y (V)']
        )
        self._curve_y_avg.setData(
            x=self._lock_in_logic.data_dict_avg['delay_position (mm)'],
            y=self._lock_in_logic.data_dict_avg['Y (V)']
        )

    # @QtCore.Slot()
    # def apply_channel_settings(self, update_logic=True):
    #     """
    #     """
    #     # channels = tuple(ch for ch, w in self._csd_widgets.items() if w['checkbox1'].isChecked())
    #     # av_channels = tuple(ch for ch, w in self._csd_widgets.items() if
    #     #                     w['checkbox2'].isChecked() and ch in channels)
    #     # Update combobox
    #     # self._mw.curr_value_comboBox.blockSignals(True)
    #     # self._mw.curr_value_comboBox.clear()
    #     # self._mw.curr_value_comboBox.addItem('None')
    #     # self._mw.curr_value_comboBox.addItems(['average {0}'.format(ch) for ch in av_channels])
    #     # self._mw.curr_value_comboBox.addItems(channels)
    #     # if self._current_value_channel is None:
    #     #     self._mw.curr_value_comboBox.setCurrentIndex(0)
    #     # else:
    #     #     index = self._mw.curr_value_comboBox.findText(self._current_value_channel)
    #     #     if index < 0:
    #     #         self._mw.curr_value_comboBox.setCurrentIndex(0)
    #     #         self._current_value_channel = None
    #     #     else:
    #     #         self._mw.curr_value_comboBox.setCurrentIndex(index)
    #     # self._mw.curr_value_comboBox.blockSignals(False)
    #     # self.current_value_channel_changed()
    #
    #     # Update plot widget axes
    #     # ch_list = self._time_series_logic.active_channels
    #     # digital_channels = tuple(ch for ch in ch_list if ch.type == StreamChannelType.DIGITAL)
    #     # analog_channels = tuple(ch for ch in ch_list if ch.type == StreamChannelType.ANALOG)
    #     # self._channels_per_axis = list()
    #     # if digital_channels:
    #     #     self._channels_per_axis.append(tuple(ch.name for ch in digital_channels))
    #     #     self._pw.setLabel('left', 'Digital Channels', units=digital_channels[0].unit)
    #     # if analog_channels:
    #     #     self._channels_per_axis.append(tuple(ch.name for ch in analog_channels))
    #     #     axis = 'right' if digital_channels else 'left'
    #     #     self._pw.setLabel(axis, 'Analog Channels', units=analog_channels[0].unit)
    #     # if analog_channels and digital_channels:
    #     #     self._pw.showAxis('right')
    #     # else:
    #     #     self._pw.hideAxis('right')
    #
    #     # Update view selection dialog
    #     # for chnl, widgets in self._vsd_widgets.items():
    #     #     # Hide corresponding view selection
    #     #     visible = chnl in channels
    #     #     av_visible = chnl in av_channels
    #     #     widgets['label'].setVisible(visible)
    #     #     widgets['checkbox1'].setVisible(visible)
    #     #     widgets['checkbox2'].setVisible(visible)
    #     #     widgets['checkbox2'].setEnabled(av_visible)
    #     #     # hide/show corresponding plot curves
    #     #     self._toggle_channel_data_plot(chnl, visible, av_visible)
    #
    #     # if update_logic:
    #     # self.sigSettingsChanged.emit(
    #     # {'active_channels': channels, 'averaged_channels': av_channels})
    #     return

    # def update_data(self):
    #     """ The function that grabs the data and sends it to the plot.
    #         If the data is 1D send it to spectrum widget, if not to image.
    #         Asks logic module to convert x-axis to target units and do corrections/normalizations.
    #         Changing axis labels accordingly.
    #         TODO: Double check if the data flipped/rotated properly.
    #     """
    #     # self._ccd_logic._proceed_data_dict['Pixels'] = self._ccd_logic._raw_data_dict['Pixels']
    #
    #     # raw_data = self._ccd_logic._raw_data_dict['Counts']
    #     # self._ccd_logic._proceed_data_dict['Counts'] = self._ccd_logic.correct_background(raw_data, self._ccd_logic._constant_background)
    #     # data = self._ccd_logic._proceed_data_dict['Counts']
    #
    #     if self._ccd_logic._raw_data_dict['Counts'] == []:
    #         return None  # TODO: Just clean some code
    #
    #     self._ccd_logic._proceed_data_dict = self._ccd_logic.convert_spectra(self._x_axis_mode, self._y_axis_mode)
    #     # data = self._ccd_logic._proceed_data_dict[self._y_axis_mode]
    #
    #     # if self._ccd_logic._x_flipped:
    #     #     self._ccd_logic.flip_data(data)
    #
    #     # Fill
    #     # self._ccd_logic._proceed_data_dict['Pixels'] = self._ccd_logic._raw_data_dict['Pixels']
    #
    #     # Convert to target units and change labels
    #
    #     if self._ccd_logic._mode == '1D':                  # Spectrum mode
    #         self._iw.clear()
    #         x_axis = self._ccd_logic._proceed_data_dict[self._x_axis_mode]
    #         # data = self._ccd_logic._proceed_data_dict[self._y_axis_mode][0]
    #         y_axis = self._ccd_logic._proceed_data_dict[self._y_axis_mode][0]
    #
    #         self._curve1.setData(x=x_axis, y=y_axis)
    #
    #         if self._x_axis_mode in ("Energy (eV)",
    #                                  "Energy (meV)",
    #                                  "Wavenumber (cm-1)",
    #                                  "Frequency (THz)",
    #                                  # "Energy RELATIVE (meV)",
    #                                  # "Frequency RELATIVE (THz)"
    #                                  ):
    #             self._sw.invertX(True)
    #         else:
    #             self._sw.invertX(False)
    #         # self._sw.plotItem.autoRange()
    #     else:                                   # Image mode
    #         self._curve1.clear()
    #         _view = self._iw.getView()
    #         _view_box = _view.getViewBox()
    #         _state = _view_box.getState()
    #
    #         self._iw.clear()
    #         self._iw.setImage(self._ccd_logic._proceed_data_dict[self._y_axis_mode])
    #         # self._iw.view.setRange(xRange=[640, 680])
    #         # self._iw.view.setRange(yRange=[0, 100])
    #         self._iw.imageItem.resetTransform()
    #
    #         if self._x_axis_mode != 'Pixels':
    #             x_axis = self._ccd_logic._proceed_data_dict[self._x_axis_mode]
    #             self._iw.imageItem.resetTransform()
    #             shape = self._ccd_logic._proceed_data_dict['Counts'].shape[0]
    #             self._iw.imageItem.translate(x_axis[0], 0)
    #             self._iw.imageItem.scale((x_axis[-1] - x_axis[0])/shape, 1)
    #             self._iw.view.getViewBox().invertY(False)
    #             aspect_ratio = shape / (x_axis[-1] - x_axis[0])
    #             self._iw.view.getViewBox().setAspectLocked(lock=True, ratio=aspect_ratio)
    #         elif self._x_axis_mode == 'Pixels':
    #             self._iw.view.getViewBox().setAspectLocked(lock=True, ratio=1)
    #
    #         if self._x_axis_mode in ("Energy (eV)",
    #                                  "Energy (meV)",
    #                                  "Wavenumber (cm-1)",
    #                                  "Frequency (THz)",
    #                                  # "Energy RELATIVE (meV)",
    #                                  # "Frequency RELATIVE (THz)"
    #                                  ):
    #             self._iw.view.getViewBox().invertX(True)
    #             self._iw.view.getViewBox().invertY(True)
    #         else:
    #             self._iw.view.getViewBox().invertX(False)
    #             self._iw.view.getViewBox().invertY(False)
    #         # self._iw.autoRange()
    #         _view_box.setState(_state)
    #
    #     # Refresh lables!
    #     self._trace_spectrum.setLabel('bottom', f'{self._x_axis_mode}')
    #     self._iw.view.setLabel('bottom', f'{self._x_axis_mode}')
    #
    #     self._trace_spectrum.setLabel('left', f'Intensity ({self._y_axis_mode})')
    #     self._iw.view.setLabel('left', f'Intensity ({self._y_axis_mode})')
    #
    # def focus_clicked(self):
    #     """ Handling the Focus button to stop and start continuous acquisition """
    #     # self._mw.number_of_spectra_spinBox.setFocus()
    #     self._mw.acquisition_Action.setDisabled(True)
    #     self._mw.save_Action.setDisabled(True)
    #     if self._ccd_logic.module_state() == 'locked':
    #         self.sigFocusStop.emit()
    #     else:
    #         self.sigFocusStart.emit()
    #
    # def acquisition_clicked(self):
    #     """ Handling the Acquisition button for getting one image/spectrum """
    #     # self.sigAcquisitionStart.emit()
    #     self._mw.focus_Action.setDisabled(True)
    #     # self._mw.acquisition_Action.setDisabled(True)
    #     self._mw.save_Action.setDisabled(True)
    #     if self._ccd_logic.module_state() == 'locked':
    #         self.sigAcquisitionStop.emit()
    #     else:
    #         self.sigAcquisitionStart.emit()
    #
    # def acquisition_finished(self):
    #     """ Change state of the buttons after finishing acquisition """
    #     self._mw.focus_Action.setDisabled(False)
    #     self._mw.acquisition_Action.setDisabled(False)
    #     self._mw.acquisition_Action.setChecked(False)
    #     self._mw.save_Action.setDisabled(False)
    #
    # def save_clicked(self):
    #     """ Handling the save button to save the data into a file.
    #     """
    #     self._ccd_logic.save_data()
    #
    # def focus_time_changed(self):
    #     self._ccd_logic.set_parameter("focus_exposure", self._mw.focus_doubleSpinBox.value())
    #
    # def acquisition_time_changed(self):
    #     self._ccd_logic.set_parameter("acquisition_exposure", self._mw.acquisition_doubleSpinBox.value())
    #
    # def laser_power_changed(self):
    #     self._ccd_logic._laser_power_mW = self._mw.laser_power_mW_doubleSpinBox.value()
    #
    # def roi_changed(self):
    #     """ ROI changed through SpinBoxes interaction """
    #     self._ccd_logic._roi[0] = self._mw.roi_x0_spinBox.value()
    #     self._ccd_logic._roi[1] = self._mw.roi_x_max_spinBox.value() - self._mw.roi_x0_spinBox.value()
    #     self._ccd_logic._roi[3] = self._mw.roi_y0_spinBox.value()
    #     self._ccd_logic._roi[4] = self._mw.roi_y_max_spinBox.value() - self._mw.roi_y0_spinBox.value()
    #     self._ccd_logic.set_parameter("roi", "baka")  # TODO: check what this line is doing.
    #
    # def bin_clicked(self, state):
    #     if state == QtCore.Qt.Checked:
    #         self._ccd_logic.set_parameter("bin", self._mw.roi_y_max_spinBox.value() - self._mw.roi_y0_spinBox.value())
    #         self._ccd_logic._mode = '1D'
    #     else:
    #         self._ccd_logic.set_parameter("bin", 1)
    #         self._ccd_logic._mode = '2D'
    #
    # def flip_clicked(self, state):
    #     """
    #     Changes the variable responsible for horizontal flipping the data. Updates spectrum/image afterwards.
    #     """
    #     if state == QtCore.Qt.Checked:
    #         self._ccd_logic._x_flipped = True
    #     else:
    #         self._ccd_logic._x_flipped = False
    #     self.update_data()
    #
    # def energy_unit_changed(self, index):
    #     box_text = self._mw.energy_selector_comboBox.currentText()
    #     self._x_axis_mode = box_text
    #     self.log.info(f"Selected x axis units: {box_text}")
    #     self.update_data()
    #
    # def counts_unit_changed(self, index):
    #     box_text = self._mw.counts_selector_comboBox.currentText()
    #     self._y_axis_mode = box_text
    #     self.log.info(f"Selected y axis units: {box_text}")
    #     self.update_data()
    #
    # def constant_background_changed(self):
    #     self._ccd_logic._constant_background = self._mw.constant_background_spinBox.value()
    #     self.update_data()
    #
    # def ccd_offset_changed(self):
    #     self._ccd_logic._ccd_offset_nm = self._mw.ccd_offset_nm_doubleSpinBox.value()
    #     self.update_data()
    #
    # def magnetic_field_changed(self):
    #     self._ccd_logic._magnetic_field_T = self._mw.magnetic_field_T_doubleSpinBox.value()
    #
    # def arbitrary_tag_changed(self):
    #     self._ccd_logic._arbitrary_tag = self._mw.arbitrary_tag_lineEdit.text()
    #
    # # TODO: Refactor this whole part. It seems it is possible to make this more elegant.

    # def adc_quality_changed(self):
    #     di = self._ccd_logic.get_availiable_values('AdcQuality')
    #     val = di[self._mw.adc_quality_comboBox.currentText()]
    #     self._ccd_logic.set_parameter_propagator('AdcQuality', val)
    #
    # def adc_analog_gain_changed(self):
    #     di = self._ccd_logic.get_availiable_values('AdcAnalogGain')
    #     val = di[self._mw.adc_analog_gain_comboBox.currentText()]
    #     self._ccd_logic.set_parameter_propagator('AdcAnalogGain', val)
    #
    # def shutter_timing_mode_changed(self):
    #     di = self._ccd_logic.get_availiable_values('ShutterTimingMode')
    #     val = di[self._mw.shutter_timing_mode_comboBox.currentText()]
    #     self._ccd_logic.set_parameter_propagator('ShutterTimingMode', val)
    #
    # def adc_speed_changed(self):
    #     val = float(self._mw.adc_speed_comboBox.currentText())
    #     self._ccd_logic.set_parameter_propagator('AdcSpeed', val)
    #
    # def vertical_shift_rate_changed(self):
    #     val = float(self._mw.vertical_shift_rate_comboBox.currentText())
    #     self._ccd_logic.set_parameter_propagator('VerticalShiftRate', val)
    #
    # def fill_interface_values(self):
    #     """
    #     Fills in available parameters for the selected camera and selects current/default values.
    #     """
    #     # for enumerated collections
    #     self._mw.adc_quality_comboBox.addItems(
    #         list(self._ccd_logic.get_availiable_values('AdcQuality').keys()))
    #     par = self._ccd_logic.get_parameter_propagator('AdcQuality')
    #     di = self._ccd_logic.get_availiable_values('AdcQuality')
    #     act = dict(map(reversed, di.items()))[par]
    #     self._mw.adc_quality_comboBox.setCurrentText(act)
    #
    #     self._mw.adc_analog_gain_comboBox.addItems(
    #         list(self._ccd_logic.get_availiable_values('AdcAnalogGain').keys()))
    #     par = self._ccd_logic.get_parameter_propagator('AdcAnalogGain')
    #     di = self._ccd_logic.get_availiable_values('AdcAnalogGain')
    #     act = dict(map(reversed, di.items()))[par]
    #     self._mw.adc_analog_gain_comboBox.setCurrentText(act)
    #
    #     self._mw.shutter_timing_mode_comboBox.addItems(
    #         list(self._ccd_logic.get_availiable_values('ShutterTimingMode').keys()))
    #     par = self._ccd_logic.get_parameter_propagator('ShutterTimingMode')
    #     di = self._ccd_logic.get_availiable_values('ShutterTimingMode')
    #     act = dict(map(reversed, di.items()))[par]
    #     self._mw.shutter_timing_mode_comboBox.setCurrentText(act)
    #
    #     # for float things
    #     self._mw.adc_speed_comboBox.addItems(
    #         list(map(str, self._ccd_logic.get_availiable_values('AdcSpeed'))))
    #     par = self._ccd_logic.get_parameter_propagator('AdcSpeed')
    #     self._mw.adc_speed_comboBox.setCurrentText(str(par))
    #
    #     self._mw.vertical_shift_rate_comboBox.addItems(
    #         list(map(str, self._ccd_logic.get_availiable_values('VerticalShiftRate'))))
    #     par = self._ccd_logic.get_parameter_propagator('VerticalShiftRate')
    #     self._mw.vertical_shift_rate_comboBox.setCurrentText(str(par))


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ex = LockInMainWindow()
    sys.exit(app.exec_())
