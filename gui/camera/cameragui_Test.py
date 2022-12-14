# -*- coding: utf-8 -*-
"""
This module contains a GUI for operating the spectrometer camera logic module.

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
import pyqtgraph as pg

from core.connector import Connector
from gui.guibase import GUIBase
from gui.colordefs import ColorScaleInferno

from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic
from gui.guiutils import ColorBar

import numpy as np

import time


class CameraSettingDialog(QtWidgets.QDialog):
    """ Create the SettingsDialog window, based on the corresponding *.ui file."""

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_camera_settings.ui')

        # Load it
        super(CameraSettingDialog, self).__init__()
        uic.loadUi(ui_file, self)


class CameraWindow(QtWidgets.QMainWindow):
    """ Class defined for the main window (not the module)

    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_camera_test_2.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class CameraGUI(GUIBase):
    """ Main spectrometer camera class.
    """

    camera_logic = Connector(interface='CameraLogic')
    savelogic = Connector(interface='SaveLogic')

    sigVideoStart = QtCore.Signal()
    sigVideoStop = QtCore.Signal()
    sigImageStart = QtCore.Signal()
    sigMeasurementStart = QtCore.Signal()
    sigMeasurementStop = QtCore.Signal()
    sigAverageStart = QtCore.Signal()

    _image = []
    _diff_measure_image = []
    _logic = None
    _mw = None

    def __init__(self, config, **kwargs):

        # load connection
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Initializes all needed UI files and establishes the connectors.
        """

        self._logic = self.camera_logic()
        self._save_logic = self.savelogic()

        self._mw = CameraWindow()
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)
        self.initSettingsUI()

        # Action buttons
        self._mw.start_video_Action.setEnabled(True)
        self._mw.start_video_Action.setChecked(self._logic.enabled)
        self._mw.start_video_Action.triggered.connect(self.start_video_clicked)

        self._mw.start_image_Action.setEnabled(True)
        self._mw.start_image_Action.setChecked(self._logic.enabled)
        self._mw.start_image_Action.triggered.connect(self.start_image_clicked)

        self._mw.start_average_Action.setEnabled(True)
        self._mw.start_average_Action.setChecked(self._logic.enabled)
        self._mw.start_average_Action.triggered.connect(self.start_average_clicked)

        self._mw.start_measure_Action.setEnabled(True)
        self._mw.start_measure_Action.setChecked(self._logic.enabled)
        self._mw.start_measure_Action.triggered.connect(self.start_measure_clicked)

        # Display update
        self._logic.sigUpdateDisplay.connect(self.update_data, QtCore.Qt.QueuedConnection)
        self._logic.sigUpdateMeasureDisplay.connect(self.update_measure_data, QtCore.Qt.QueuedConnection)
        self._logic.sigUpdateImageDisplay.connect(self.update_image_data, QtCore.Qt.QueuedConnection)
        self._logic.sigAcquisitionFinished.connect(self.acquisition_finished, QtCore.Qt.QueuedConnection)
        self._logic.sigVideoFinished.connect(self.enable_start_image_action, QtCore.Qt.QueuedConnection)
        self._logic.sigMeasureFinished.connect(self.enable_start_action)

        # starting the physical measurement
        self.sigVideoStart.connect(self._logic.start_loop, QtCore.Qt.QueuedConnection)
        self.sigVideoStop.connect(self._logic.stop_loop, QtCore.Qt.QueuedConnection)
        self.sigImageStart.connect(self._logic.start_single_acquistion, QtCore.Qt.QueuedConnection)

        self.sigMeasurementStart.connect(self._logic.start_voltage_measurements)
        self.sigMeasurementStop.connect(self._logic.stop_voltage_measurements)

        # self.sigMeasurementStop.connect(self._logic.stop_loop)
        # test measure
        self.sigAverageStart.connect(self._logic.measure_start_loop)
        # self.sigMeasurementStop.connect(self._logic.measure_stop_loop)

        # change value field
        self._mw.average_SpinBox.lineEdit().returnPressed.connect(self.change_measure_value)

        self._mw.label_start_voltage.setText('Start voltage: ' + str(self._logic._start_volt) + 'V')
        self._mw.start_voltage_SpinBox.lineEdit().returnPressed.connect(self.change_start_value)
        self._mw.start_voltage_SpinBox.setRange(self._logic._minV, self._logic._maxV)

        self._mw.label_stop_voltage.setText('Stop voltage: ' + str(self._logic._stop_volt) + 'V')
        self._mw.stop_voltage_SpinBox.lineEdit().returnPressed.connect(self.change_stop_value)
        self._mw.stop_voltage_SpinBox.setRange(self._logic._minV, self._logic._maxV)

        self._mw.label_step.setText('Step: ' + str(self._logic._step_volt) + 'V')
        self._mw.step_SpinBox.lineEdit().returnPressed.connect(self.change_step_value)
        self._mw.step_SpinBox.setRange(-100,100)
        #self._mw.wait_time_DoubleSpinBox.valueChanged.connect(self.change_measure_value)

        # Get measure image
        diff_data_image = self._logic.get_diff_av_image()
        self._diff_measure_image = pg.ImageItem(image=diff_data_image, axisOrder='row-major')
        self._mw.image_PlotWidget_2.addItem(self._diff_measure_image)
        self._mw.image_PlotWidget_2.setAspectLocked(True)

        # connect Settings action under Options menu
        self._mw.actionSettings.triggered.connect(self.menu_settings)
        # connect save action to save function
        self._mw.actionSave_XY_Scan.triggered.connect(self.save_xy_scan_data)

        raw_data_image = self._logic.get_last_image()
        self._image = pg.ImageItem(image=raw_data_image, axisOrder='row-major')
        self._mw.image_PlotWidget.addItem(self._image)
        self._mw.image_PlotWidget.setAspectLocked(True)

        # Get the colorscale and set the LUTs
        self.my_colors = ColorScaleInferno()

        self._image.setLookupTable(self.my_colors.lut)

        # Connect the buttons and inputs for the colorbar
        self._mw.xy_cb_manual_RadioButton.clicked.connect(self.update_xy_cb_range)
        self._mw.xy_cb_centiles_RadioButton.clicked.connect(self.update_xy_cb_range)

        self._mw.xy_cb_min_DoubleSpinBox.valueChanged.connect(self.shortcut_to_xy_cb_manual)
        self._mw.xy_cb_max_DoubleSpinBox.valueChanged.connect(self.shortcut_to_xy_cb_manual)
        self._mw.xy_cb_low_percentile_DoubleSpinBox.valueChanged.connect(self.shortcut_to_xy_cb_centiles)
        self._mw.xy_cb_high_percentile_DoubleSpinBox.valueChanged.connect(self.shortcut_to_xy_cb_centiles)

        # create color bar
        self.xy_cb = ColorBar(self.my_colors.cmap_normed, width=100, cb_min=0, cb_max=100)
        self.depth_cb = ColorBar(self.my_colors.cmap_normed, width=100, cb_min=0, cb_max=100)
        self._mw.xy_cb_ViewWidget.addItem(self.xy_cb)
        self._mw.xy_cb_ViewWidget.hideAxis('bottom')
        self._mw.xy_cb_ViewWidget.setLabel('left', 'Fluorescence', units='c')
        self._mw.xy_cb_ViewWidget.setMouseEnabled(x=False, y=False)

        self._mw.label_default_average.setText('default_av = ' + str(self._logic._average))
        # self._mw.label_default_wait_time.setText('default_wt = ' + str(self._logic._wait_time))

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def initSettingsUI(self):
        """ Definition, configuration and initialisation of the settings GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        Moreover it sets default values if not existed in the logic modules.
        """
        # Create the Settings window
        self._sd = CameraSettingDialog()
        # Connect the action of the settings window with the code:
        self._sd.accepted.connect(self.update_settings)
        self._sd.rejected.connect(self.keep_former_settings)
        self._sd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.update_settings)

        # write the configuration to the settings window of the GUI.
        self.keep_former_settings()

    def update_settings(self):
        """ Write new settings from the gui to the file. """
        self._logic.set_exposure(self._sd.exposureDSpinBox.value())
        self._logic.set_gain(self._sd.gainSpinBox.value())

    def keep_former_settings(self):
        """ Keep the old settings and restores them in the gui. """
        self._sd.exposureDSpinBox.setValue(self._logic._exposure)
        self._sd.gainSpinBox.setValue(self._logic._gain)

    def menu_settings(self):
        """ This method opens the settings menu. """
        self._sd.exec_()

    def start_average_clicked(self):

        self.sigAverageStart.emit()
        self._mw.start_measure_Action.setDisabled(True)
        self._mw.start_image_Action.setDisabled(True)
        self._mw.start_video_Action.setDisabled(True)
        self._mw.start_average_Action.setDisabled(True)

    def start_measure_clicked(self):
        self._mw.start_image_Action.setDisabled(True)
        self._mw.start_video_Action.setDisabled(True)
        self._mw.start_average_Action.setDisabled(True)

        if self._logic.enabled == True:
            self._mw.start_measure_Action.setText('Start Measure')
            self._logic.volt_free = False
            self.sigMeasurementStop.emit()
        else:
            self._mw.start_measure_Action.setText('Stop Measure')
            self._logic.volt_free = True
            self.sigMeasurementStart.emit()


    def start_image_clicked(self):

        self.sigImageStart.emit()
        self._mw.start_average_Action.setDisabled(True)
        self._mw.start_measure_Action.setDisabled(True)
        self._mw.start_image_Action.setDisabled(True)
        self._mw.start_video_Action.setDisabled(True)

    def acquisition_finished(self):

        self._mw.start_image_Action.setChecked(False)
        self._mw.start_image_Action.setDisabled(False)

        self._mw.start_video_Action.setChecked(False)
        self._mw.start_video_Action.setDisabled(False)

        self._mw.start_measure_Action.setChecked(False)
        self._mw.start_measure_Action.setDisabled(False)

        self._mw.start_average_Action.setChecked(False)
        self._mw.start_average_Action.setDisabled(False)

    def start_video_clicked(self):
        """ Handling the Start button to stop and restart the counter.
        """
        self._mw.start_image_Action.setDisabled(True)
        self._mw.start_measure_Action.setDisabled(True)
        self._mw.start_average_Action.setDisabled(True)

        if self._logic.enabled == True:
            self._logic.free = False
            self._mw.start_video_Action.setText('Start Video')
            self.sigVideoStop.emit()
        else:
            self._mw.start_video_Action.setText('Stop Video')
            self._logic.free = True
            self.sigVideoStart.emit()

            #self._logic.sigStartVideo.emit()

    def enable_start_image_action(self):
        self._mw.start_image_Action.setEnabled(True)
        self._mw.start_average_Action.setEnabled(True)
        self._mw.start_measure_Action.setEnabled(True)

    def enable_start_action(self):

        # if self._logic.enabled == True:
        #     self._mw.start_measure_Action.setText('Start Measure')
        #     self._logic.volt_free = False
        #     #self.sigMeasurementStop.emit()
        # else:
        #     self._mw.start_measure_Action.setText('Stop Measure')
        #     self._logic.volt_free = True
            #self.sigMeasurementStart.emit()
        self._mw.start_measure_Action.setText('Start Measure')
        self._logic.volt_free = False
        self._logic.enabled = False
        self._logic.sigAcquisitionFinished.emit()
        self._mw.start_average_Action.setEnabled(True)
        self._mw.start_image_Action.setEnabled(True)
        self._mw.start_video_Action.setEnabled(True)

    def update_data(self):
        """
        Get the image data from the logic and print it on the window
        """
        if self._logic.free:
            #self._logic.sigNewFrame.emit()
            #raw_data_image = self._logic._last_image
            raw_data_image = self._logic.continuous_get_data()
            levels = (0., 1.)
            # self._image.setImage(image=raw_data_image, levels=levels)
            self._image.setImage(image=raw_data_image)
            # self.update_xy_cb_range()
            self._logic.sigUpdateDisplay.emit()

    def update_image_data(self):
        """
        Get the image data from the logic and print it on the window
        """
        raw_data_image = self._logic.get_last_image()
        levels = (0., 1.)
        self._image.setImage(image=raw_data_image)

    def update_measure_data(self):
        """
        Get the image data from the logic and print it on the window
        """
        diff_data_image = self._logic.get_diff_av_image()
        levels = (0., 1.)
        self._diff_measure_image.setImage(image=diff_data_image)
        # self.update_xy_cb_range()
        # self._image.setImage(image=raw_data_image, levels=levels)

    def updateView(self):
        """
        Update the view when the model change
        """
        pass

    # color bar functions
    def get_xy_cb_range(self):
        """ Determines the cb_min and cb_max values for the xy scan image
        """
        # If "Manual" is checked, or the image data is empty (all zeros), then take manual cb range.
        if self._mw.xy_cb_manual_RadioButton.isChecked() or np.max(self._image.image) == 0.0:
            cb_min = self._mw.xy_cb_min_DoubleSpinBox.value()
            cb_max = self._mw.xy_cb_max_DoubleSpinBox.value()

        # Otherwise, calculate cb range from percentiles.
        else:
            # xy_image_nonzero = self._image.image[np.nonzero(self._image.image)]

            # Read centile range
            low_centile = self._mw.xy_cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.xy_cb_high_percentile_DoubleSpinBox.value()

            cb_min = np.percentile(self._image.image, low_centile)
            cb_max = np.percentile(self._image.image, high_centile)

        cb_range = [cb_min, cb_max]

        return cb_range

    def refresh_xy_colorbar(self):
        """ Adjust the xy colorbar.

        Calls the refresh method from colorbar, which takes either the lowest
        and higherst value in the image or predefined ranges. Note that you can
        invert the colorbar if the lower border is bigger then the higher one.
        """
        cb_range = self.get_xy_cb_range()
        self.xy_cb.refresh_colorbar(cb_range[0], cb_range[1])

    def refresh_xy_image(self):
        """ Update the current XY image from the logic.

        Everytime the scanner is scanning a line in xy the
        image is rebuild and updated in the GUI.
        """
        self._image.getViewBox().updateAutoRange()

        xy_image_data = self._logic._last_image

        cb_range = self.get_xy_cb_range()

        # Now update image with new color scale, and update colorbar
        self._image.setImage(image=xy_image_data, levels=(cb_range[0], cb_range[1]))
        self.refresh_xy_colorbar()

    def shortcut_to_xy_cb_manual(self):
        """Someone edited the absolute counts range for the xy colour bar, better update."""
        self._mw.xy_cb_manual_RadioButton.setChecked(True)
        self.update_xy_cb_range()

    def shortcut_to_xy_cb_centiles(self):
        """Someone edited the centiles range for the xy colour bar, better update."""
        self._mw.xy_cb_centiles_RadioButton.setChecked(True)
        self.update_xy_cb_range()

    def update_xy_cb_range(self):
        """Redraw xy colour bar and scan image."""
        self.refresh_xy_colorbar()
        self.refresh_xy_image()

    # save functions

    def save_xy_scan_data(self):
        """ Run the save routine from the logic to save the xy confocal data."""
        cb_range = self.get_xy_cb_range()

        # Percentile range is None, unless the percentile scaling is selected in GUI.
        pcile_range = None
        if not self._mw.xy_cb_manual_RadioButton.isChecked():
            low_centile = self._mw.xy_cb_low_percentile_DoubleSpinBox.value()
            high_centile = self._mw.xy_cb_high_percentile_DoubleSpinBox.value()
            pcile_range = [low_centile, high_centile]

        self._logic.save_xy_data(colorscale_range=cb_range, percentile_range=pcile_range)

        # TODO: find a way to produce raw image in savelogic.  For now it is saved here.
        filepath = self._save_logic.get_path_for_module(module_name='Confocal')
        filename = filepath + os.sep + time.strftime('%Y%m%d-%H%M-%S_confocal_xy_scan_raw_pixel_image')

        self._image.save(filename + '_raw.png')

    def change_measure_value(self):
        """Change average and wait time value"""
        self._logic._average = self._mw.average_SpinBox.value()
        self._mw.label_default_average.setText('default_av = ' + str(self._logic._average))

    def change_start_value(self):
        self._mw.label_start_voltage.setText('Start voltage: ' + str(self._mw.start_voltage_SpinBox.value()) + 'V')
        self._logic._start_volt = self._mw.start_voltage_SpinBox.value()

    def change_stop_value(self):
        self._mw.label_stop_voltage.setText('Stop voltage: ' + str(self._mw.stop_voltage_SpinBox.value()) + 'V')
        self._logic._stop_volt = self._mw.stop_voltage_SpinBox.value()

    def change_step_value(self):
        self._mw.label_step.setText('Step: ' + str(self._mw.step_SpinBox.value()) + 'V')
        self._logic._step_volt = self._mw.step_SpinBox.value()
