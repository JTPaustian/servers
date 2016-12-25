# Copyright (C) 2016 Noah Meltzer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

__author__ = "Noah Meltzer"
__copyright__ = "Copyright 2016, McDermott Group"
__license__ = "GPL"
__version__ = "2.0.1"
__maintainer__ = "Noah Meltzer"
__status__ = "Beta"


import atexit
import threading
import sys
import traceback

import labrad

from dataChestWrapper import dataChestWrapper
# Import nGui tools.
from MFrame import MFrame
import MPopUp

sys.dont_write_bytecode = True


class Device:
    """The device class handles a LabRAD device."""
    def __init__(self,name):
        # Get all the stuff from the constructor.
        # Has a the device made an appearance, this is so we dont alert
        # the user more than once if a device dissapears.
        self.foundDevice = False
        self.name = name
        # Nicknames of settings (the ones that show up on the GUI).
        self.nicknames = []
        # Units for the settings to be used with the values on the GUI.
        self.settingUnits = []
        # List of the precisions for the values on the GUI.
        self.settingPrecisions = []
        # List of settings that the user wants run on their device.
        settings = []
        # The actual names of the settings.
        self.settingNames = []
        # Stores the actual reference to the labrad server.
        deviceServer = None
        # True if device is functioning correctly.
        self.isDevice = False
        # Used for device.select_device(selectedDevice) setting.
        self.selectedDevice = 0
        # Store the setting to select device (almost always 'select_device').
        self.setDeviceCmd = None    
        # Store the buttons along with their parameters.
        buttons = [[]]
        # Arguments that should be passed to settings if necessary.
        self.settingArgs =[]    
        self.settingResultIndices = []
        self.frame = MFrame()
        self.frame.setYLabel(None)
        # Determine which buttons get messages.
        self.buttonMessages = []
        # Setup all buttons.
        self.buttonNames = []
        self.buttonSettings = []
        self.buttons = []
        # Datachest wrapper.
        self.datachest = dataChestWrapper(self)
        # Tells thread to keep going.
        self.keepGoing = True
        atexit.register(self.stop)
    
    def stop(self):
        self.keepGoing = False
        
    def setServerName(self, name):
        self.serverName = name
        
    def addParameter(self, parameter, setting, arg=None, index=None,
            units=None, precision=2):
        self.settingNames.append(setting)
        self.settingResultIndices.append(index)
        self.nicknames.append(parameter)
        self.settingArgs.append(arg)
        self.settingUnits.append(units)
        self.settingPrecisions.append(precision)
        
    def connection(self, cxn):
        self.cxn = cxn
        self.ctx = cxn.context()

    def addButton(self, name, msg, setting, arg=None):
        self.buttons.append([])
        i = len(self.buttons) - 1
        self.buttons[i].append(name)
        self.buttons[i].append(setting)
        self.buttons[i].append(msg)
        self.buttons[i].append(arg)
        self.frame.setButtons(self.buttons)
        
    def setYLabel(self, yLbl, units=''):
        self.frame.setYLabel(yLbl, units)

    def selectDeviceCommand(self, cmd, arg):
        self.selectedDevice = arg   
        self.setDeviceCmd = cmd 
    
    def begin(self):
        self.frame.setTitle(self.name)
        self.frame.setNicknames(self.nicknames)
        self.frame.setReadingIndices(self.settingResultIndices)
        # Each device NEEDS to run on a different thread 
        # than the main thread (which ALWAYS runs the gui).
        # This thread is responsible for querying the devices.
        self.deviceThread = threading.Thread(target=self.Query, args=[])
        # If the main thread stops, stop the child thread.
        self.deviceThread.daemon = True
        # Start the thread.
        self.deviceThread.start()

    def setRefreshRate(self, period):
        #self.refreshRateSec = period
        self.frame.setRefreshRate(period)

    def setPlotRefreshRate(self, period):
        self.frame.setPlotRefreshRate(period)

    def addPlot(self, length=None):
        self.frame.addPlot(length)
        # Datalogging must be enabled if we want to plot data.
        self.frame.enableDataLogging(True)
        return self.frame.getPlot()

    def connect(self):  
        '''Connect to the device'''
        try:
            # Attempt to connect to the server given the connection 
            # and the server name.
            self.deviceServer = getattr(self.cxn, self.serverName)()
            # If the select device command is not none, run it.
            if self.setDeviceCmd is not None:
                getattr(self.deviceServer, self.setDeviceCmd)(
                    self.selectedDevice, context = self.ctx)
            # True means successfully connected.
            self.foundDevice = False
            print("Found device: %s" %self.serverName)
            return True
        except labrad.client.NotFoundError, AttributeError:
            if not self.foundDevice:
                self.foundDevice = True
                print("Unable to find device: %s" %self.serverName)
            self.frame.raiseError("LabRAD issue")
        except:
            # The nFrame class can pass an error along with a message.
            self.frame.raiseError("LabRAD issue")
            
            return False
        
    def getFrame(self):
        '''Return the device's frame'''
        return self.frame

    def logData(self, b):
        self.frame.enableDataLogging(b)

    def prompt(self, button):
        '''If a button is clicked, handle it.'''
        try:
            # If the button has a warning message attatched.
            if self.frame.getButtons()[button][2] is not None:
                # Create a new popup.
                self.warning = MPopUp.PopUp(self.frame.getButtons()
                    [button][2])
                # Stop the main gui thread and run the popup.
                self.warning.exec_()
                # If and only if the 'ok' button is pressed.
                if self.warning.consent:
                    # If the setting associated with the button also 
                    # has an argument for the setting.
                    if(self.frame.getButtons()[button][3] is not None):
                        getattr(self.deviceServer, self.frame.getButtons()
                            [button][1])(self.frame.getButtons()
                            [button][4])
                    # If just the setting needs to be run.
                    else:
                        getattr(self.deviceServer, self.frame.getButtons()
                            [button][1])
            # Otherwise if there is no warning message, do not make a popup.
            else:
                # If there is an argument that must be passed to the setting.
                if(self.frame.getButtons()[button][3] is not None):
                    getattr(self.deviceServer, self.frame.getButtons()
                        [button][1])(self.frame.getButtons()[button][4])
                else:
                    getattr(self.deviceServer, self.frame.getButtons()
                        [button][1])
        except:
            traceback.print_exc()
            return

    def Query(self):
        '''Ask the device for readings'''
        # If the device is attatched.
       
        if not self.isDevice:
            # Try to connect again, if the value changes, then we know 
            # that the device has connected.
            if self.connect() is not self.isDevice:
                self.isDevice = True
        # Otherwise, if the device is already connected.
        else:
            try:
                readings = []   # Stores the readings.
                units = []      # Stores the units.
                precisions = []
                for i in range(len(self.settingNames)):
                    # If the setting needs to be passed arguments
                    if self.settingArgs[i] is not None:
                        reading = getattr(self.deviceServer,
                                self.settingNames[i])(self.settingArgs[i],
                                context=self.ctx)
                    else:
                        reading = getattr(self.deviceServer,
                                self.settingNames[i])(context=self.ctx)
                    # If the reading has a value and units.
                    if isinstance(reading, labrad.units.Value):
                        pass
                    # If the reading is an array of values and units.
                    elif isinstance(reading, labrad.units.ValueArray):
                        if self.settingResultIndices != None and \
                                isinstance(reading[self.settingResultIndices[i]],
                                        labrad.units.Value):
                            reading = reading[self.settingResultIndices[i]]
                        elif len(reading) == 1:
                            reading = reading[0]
                        else:
                            reading = reading[i]
                            
                    if isinstance(reading, labrad.units.Value):
                        preferredUnits = self.settingUnits[i]
                        if preferredUnits is not None and \
                                reading.isCompatible(preferredUnits):
                            reading = reading.inUnitsOf(preferredUnits)
                        u = reading.units
                        readings.append(reading[u])
                        units.append(u)
                        precisions.append(self.settingPrecisions[i])
                    elif type(reading) is list:
                        for j in range(len(reading)):
                            single_reading = reading[j]
                            if isinstance(single_reading, labrad.units.Value):
                                preferredUnits = self.settingUnits[i]
                                if preferredUnits is not None and \
                                        single_reading.isCompatible(preferredUnits):
                                    single_reading = single_reading.inUnitsOf(preferredUnits)
                                u = single_reading.units
                                readings.append(single_reading[u])
                                units.append(u)
                                precisions.append(self.settingPrecisions[i])
                            else:
                                readings.append(reading[i])
                                units.append("")
                                precisions.append(self.settingPrecisions[i])
                    else:
                        try:
                            readings.append(reading)
                            units.append("")
                            precisions.append(self.settingPrecisions[i])
                        except:
                            print("Problem with readings, type '%s' "
                                    "cannot be displayed"
                                    %str(type(reading)))
                # Pass the readings and units to the frame.
                self.frame.setReadings(readings)
                self.frame.setUnits(units)
                self.frame.setPrecisions(precisions)
                # Save the data.
                self.datachest.save()
                # If there was an error, retract it.
                self.frame.retractError()
            except IndexError as e:
                traceback.print_exc()
                print("[%s] Something appears to be wrong with what "
                      "the labrad server is returning: "
                      %str(self.frame.getTitle()))
                print("\tReading: %s" %str(readings))
                print("\tUnits: %s" %units)
                print("\t%s" %str(e))
            except:
                traceback.print_exc()
                self.frame.raiseError("Problem communicating with %s"
                        %self.name)
                self.frame.setReadings(None)
                self.isDevice = False
        # Query calls itself again, this keeps the thread alive.
        if self.keepGoing:
            threading.Timer(self.frame.getRefreshRate(), self.Query).start()
        return