# Copyright 2019 Alexandru Sonea. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================
"""Module defining the base classes.

The base classes for Bus, Device and Robot are defined here. Specific
classes for dedicated bus and device processing will be derived from
these classes.
"""


from roboglia.utils import readIniFile


class BaseBus():
    """A base abstract class for handling an arbitrary bus.

    You will normally subclass `BaseBus` and define particular functionality
    specific to the bus by impementing the methods of the `BaseBus`.
    This class only stores the name of the bus and the access to the
    physical object. Your subclass can add additional attributes and 
    methods to deal with the particularities of the real bus represented.

    Parameters
    ---------
    name
        A string used to identify the bus.

    port
        A string that indentifies technically the bus. For instance a
        serial bus would be `/dev/ttyUSB0` while an SPI bus might be
        represented as `0` only (indicating the SPI 0 bus).

    """
    def __init__(self, name, port):
        """Initializes the bus information.


        """
        self.name = name
        self.port = port

    def open(self):
        """Opens the actual physical bus. Must be overriden by the
        subclass.

        """
        pass

    def close(self):
        """Closes the actual physical bus. Must be overriden by the
        subclass.

        """
        pass

    def isOpen(self):
        """Returns `True` or `False` if the bus is open. Must be overriden 
        by the subclass.

        """
        return False


class BaseRegister():
    
    def __init__(self, reginfo):
        self.address = int(reginfo['Address'])
        self.access = reginfo['Access']
        self.sync = reginfo['Sync']
        self.int_value = 0

    @property
    def value(self):
        return self.valueToExternal(self.int_value)

    @value.setter
    def value(self, value):
        self.int_value = self.valueToInternal(value)

    def valueToExternal(self, value):
        return value

    def valueToInternal(self, value):
        return int(value)


class BaseDevice():
    """A base virtual class for all devices.

    A BaseDevice is a surrogate representation of an actual device,
    characterised by a number of internal registers that can be read or
    written to by the means of a coomunication bus.
    Any device is based on a `model` that identifies the `.device` file
    describing the structure of the device (the registers).

    Parameters
    ----------
    name : str
        The name that the created device will be associated with. Ex.
        it could be 'l_arm_p' for a Dynamixel servo representing the 
        left arm pitch joint, or it could be 'imu_accel' for the device
        describing the accelerometer.

    model : str
        The name of the device type that is used to initialize its
        structure. A file `.device` needs to be located and parsed 
        successfully in order to the construction of the device to
        be completed. The locatization of the `.device` file is performed
        by the method `getModelPath()` that can return different paths for
        different devices and can be oveloaded by a custom subclass that
        uses custom `.device` files located outside of the main package.

    bus : BaseBus or subclass
        It is the bus that the device uses to read or write values when
        syncronising with the actual device.

    Attributes
    ----------
    name : str
        The name of the device.

    bus : object
        The bus that operates the device.

    registers : dict of objects
        A dictionary with the imutable data of the device's registries
        as loaded from the model `.device` file and initialized.

    values : dict of int
        A dictionary with the current values of the registers. Please note
        that the synchronisation with the physical device must be 
        implemented separatelly.
    """
    def __init__(self, model, bus, dev_id):
        self.bus = bus
        self.dev_id = dev_id
        self.registers = {}
        model_file = self.getModelPath(model)
        model_ini = readIniFile(model_file)
        for reginfo in model_ini['registers']:
            new_register = self.initRegister(reginfo)
            self.__dict__[reginfo['Name']] = new_register
            self.registers[reginfo['Name']] = new_register


    def getModelPath(self, model):
        """Builds the path to the `.device` documents.

        For BaseDevice it will return a file path located in the directory
        `devices` imediately under the current directory of the Python 
        modeule code.

        Returns
        -------
        str
            A full document path including the name of the model and the
            externasion `.device`.
        """
        pass

    def initRegister(self, reginfo):
        """Default processing method for setting up a register.

        Does nothhing in the case of a BaseDevice and subclasses need to
        define their own internal format for the registers. This method
        should return a fully initialized register class based on the 
        information included in `reginfo`.

        Parameters
        ----------
        reginfo : dict
            A dictionry with the register attributes and values.

        Returns
        -------
        object
            An allocated registered which normally should be a
            `namedtuple` class with the attributes of the regiter 
            initialized from the `reginfo` dictionary.
        """
        return BaseRegister(reginfo)

    def pullRegister(self, regname):
        if regname not in self.registers:
            raise KeyError("Register {} does not exist")
        else:
            return True

    def pushRegister(self, regname):
        if regname not in self.registers:
            raise KeyError("Register {} does not exist")
        reg = self.registers[regname]
        if reg.access == 'R':
            raise ValueError("Register {} is read-only. Cannot pushRegister()")
        else:
            return True

    def pullRegisterList(self, reglist=[]):
        result = []
        for register in reglist:
            result.append(self.pullRegister(register))
        return result

    def pushRegisterList(self, reglist=[]):
        result = []
        for register in reglist:
            result.append(self.pushRegister(register))
        return result

    def pullAllRegisters(self):
        result = []
        for register in self.registers.keys():
            result.append(self.pullRegister(register))
        return result

    def pushAllRegisters(self):
        result = []
        for register in self.registers.keys():
            result.append(self.pushRegister(register))
        return result


class BaseRobot():

    def __init__(self, ini_file):
        config = readIniFile(ini_file)
        self.buses = {}
        self.devices = {}

        # load the bus configuration
        for businfo in config['buses']:
            new_bus = self.processBus(businfo)
            self.buses[businfo['Name']] = new_bus
        
        # load the devices
        for device in config['devices']:
            new_device = self.processDevice(device, self.buses[device['Bus']])

            self.devices[device['Name']] = new_device
            self.buses[device['Bus']].devices.append(new_device)


    def processBus(self, businfo):
        """BaseRobot only knows BaseBus and this default method
        will allocate one. Subclasses should override this method and
        implement allocation for all the device classes they use.
        """
        if businfo['Class'] == 'BaseBus':
            return BaseBus(businfo['Name'], businfo['Port'])
        else:
            raise KeyError('Unknown bus class name: {}'.format(businfo['Class']))


    def processDevice(self, devinfo, bus):
        if devinfo['Class'] == 'BaseDevice':
            return BaseDevice(devinfo['Model'], bus, devinfo['Id'])
        else:
            raise KeyError('Unknown device class name {}'.format(devinfo['Class']))


    def __getattr__(self, attr):
        if attr in self.devices:
            return self.devices[attr]
        else:
            raise AttributeError(f'{self.__class__.__name__}.{attr} is invalid.')        