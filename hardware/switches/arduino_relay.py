# -*- coding: utf-8 -*-

"""
This file contains the hardware control the simple arduino UNO relay

You have to install drivers (CH340) to communicate with it via USB

qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import pyvisa as visa
import time
from enum import Enum

from core.module import Base
from core.configoption import ConfigOption

from interface.switch_interface import SwitchInterface


class ArduinoRelay(Base, SwitchInterface):
    """
    Main class for the arduino relay.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    _modclass = 'relay'
    _modtype = 'hardware'

    _state = 'positive'
    _switch_name = "Arduino UNO relay"

    _switch_states = ConfigOption(name='switch_states', default=['positive', 'negative'], missing='nothing')
    _hardware_name = ConfigOption(name='name', default='arduino uno relay', missing='nothing')

    _com_port_relay = ConfigOption('com_port_relay', 'ASRL8::INSTR', missing='warn')

    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        """
        self.connect()

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self.disconnect()

    def connect(self):
        """In contrast to brushless delay line here is no external controller,
           so we can connect directly to delay line avoiding
           controller_handel and channel selection procedures
        """
        self.rm = visa.ResourceManager('@py')
        try:
            self._relay_handle = self.rm.open_resource(self._com_port_relay, baud_rate=115200)
            self.log.info("Arduino relay is connected")
        except:
            self.log.warning('Cannot connect to the arduino relay! Check ports!')

    def disconnect(self):
        self._relay_handle.close()

    def name(self):
        return self._hardware_name

    @property
    def states(self):
        """ The current states the hardware is in as state dictionary with switch names as keys and
        state names as values.

        @return dict: All the current states of the switches in the form {"switch": "state"}
        """
        # with self.lock:
        return {switch: self.get_state(switch) for switch in self.available_states}

    @property
    def available_states(self):
        name = self.name()
        return {name: self._switch_states}

    def get_state(self, switch):
        return self._state

    def set_state(self, switch, state):
        if state == "positive":
            self._relay_handle.write('1')
            self._state = "positive"
        if state == "negative":
            self._relay_handle.write('0')
            self._state = "negative"
        return 0
