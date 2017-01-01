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
__version__ = "1.5.2"
__maintainer__ = "Noah Meltzer"
__status__ = "Beta"


class MFrame:
  
    def __init__(self):
        """This class acts as the interface between the devices and all
    classes which use the device or any of its parameters."""
        # Name of device's server.
        self.serverTitle = None
        # Parameter names to be displayed on the GUI.
        self.nicknames = None
        # Settings which are called by the GUI.
        self.serverSettings = None
        # Device readings.
        self.readings = None
        # Precisions.
        self.precisions = None
        # Errors.
        self.error = False
        # Error messages.
        self.errmsg = None
        # Label on the y axis of the dataChest dataplot.
        self.yLabel = ""
        # Units used for each parameter.
        self.units = []
        # Buttons on the GUI used to control the device.
        self.buttons = [[]]
        # Stores an index of a certain button.
        self.buttonInd = None
        # Is a specified button pushed?
        self.buttonPushed = False
        # Store the plots.
        self.isPlotBool = False
        # Just in case the user wants to label their NGui plot with
        # custom units (note these are only the units displayed onscreen,
        # not the units that the data is logged with).
        self.custUnits = ''
        # If the length of the graph should be plotted over a fixed interval.
        self.plotLength = None
        # Hold the datachest object.
        self.dataSet = None
        # Hold the plot.
        self.plot = None
        # Refresh rate of plot.
        self.plotRefreshRate = 1
        # RefreshRate for the device.
        self.refreshRate = 1
        # Datalogging disabled by default
        self.logData = False
        # Dictionary holding datalogging settings
        self.datalogsettingsDict = {
                "enabled"   :    self.logData,
                "location":     None,
                "dataset"   :     self.dataSet
                }
        # Is there a reading out of range?
        self.outOfRange = {}

    def setTitle(self, title):
        self.serverTitle = title

    def getTitle(self):
        return self.serverTitle

    def getNicknames(self):
        return self.nicknames

    def setNicknames(self, nicknames):
        self.nicknames = nicknames

    def setReadings(self, readings):
        self.readings = readings

    def getReadings(self):
        return self.readings
        
    def setPrecisions(self, precisions):
        self.precisions = precisions

    def getPrecisions(self):
        return self.precisions
        
    def setReadingIndices(self, index):
        self.readingIndices = index

    def getReadingIndices(self):
        return self.readingIndices
       
    def raiseError(self, msg):
        self.error = True
        self.errmsg = msg

    def retractError(self):
        self.error = False
        self.errmsg = None

    def isError(self):
        return self.error

    def errorMsg(self):
        return self.errmsg

    def setUnits(self, units):
        self.units = units

    def getUnits(self):
        return self.units

    def getCustomUnits(self):
        return self.custUnits

    def getButtons(self):
        return self.buttons

    def setButtons(self, buttons):
        self.buttons = buttons

    def buttonPressed(self, buttonInd):
        self.buttonInd = buttonInd
        self.buttonPushed = True

    def getButtonPressed(self):
        self.buttonPushed = False
        return self.buttonInd

    def isButtonPressed(self):
        return self.buttonPushed

    def setYLabel(self, y, custUnits=''):
        self.custUnits = custUnits
        self.yLabel = y

    def getYLabel(self):
        return self.yLabel

    def addPlot(self, length = None):
        self.isPlotBool=True
        self.plotLength = length

    def isPlot(self):
        return self.isPlotBool

    def setPlot(self, p):
        self.plot = p

    def getPlot(self):
        return self.plot

    def setPlotRefreshRate(self, period):
        self.plotRefreshRate = period

    def getPlotRefreshRate(self):
        return self.plotRefreshRate

    def setRefreshRate(self, period):
        self.refreshRate = period

    def getRefreshRate(self):
        return self.refreshRate

    def getPlotLength(self):
        return self.plotLength

    def setDataSet(self, dataSet):
        self.dataSet = dataSet

    def getDataSet(self):
        return self.dataSet

    def enableDataLogging(self, b):
        self.logData = b

    def isDataLogging(self):
        return self.logData
        
    def DataLoggingInfo(self):
        return self.datalogsettingsDict
        
    def getOutOfRangeStatus(self): 
        return self.outOfRange
        
    def setOutOfRange(self, key):
        self.outOfRange[key] = True

    def setInRange(self, key):
        self.outOfRange[key] = False

    def disableRange(self):
      self.outOfRange = {key: False for key in self.outOfRange}
      