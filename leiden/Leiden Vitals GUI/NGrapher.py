# Copyright (C) 2016 Noah Meltzer and the internet
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


"""
version = 1.1.0
description = Adds graphing functionality
"""

from __future__ import unicode_literals
import sys
import os
import random
from matplotlib.backends import qt_compat
use_pyside = qt_compat.QT_API == qt_compat.QT_API_PYSIDE
if use_pyside:
	from PySide import QtGui, QtCore
else:
	from PyQt4 import QtGui, QtCore

from numpy import arange, sin, pi
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import rc
progname = os.path.basename(sys.argv[0])
progversion = "0.1"


class MyMplCanvas(FigureCanvas):
	"""Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""

	def __init__(self, parent=None, width=5, height=4, dpi=100):
		fig = Figure(figsize=(5, 4), dpi=100)
		self.axes = fig.add_subplot(111)
		# We want the axes cleared every time plot() is called
		self.axes.hold(False)

		#self.compute_initial_figure()

		#
		FigureCanvas.__init__(self, fig)
		self.setParent(parent)

		FigureCanvas.setSizePolicy(self,
								   QtGui.QSizePolicy.Expanding,
								   QtGui.QSizePolicy.Expanding)
		FigureCanvas.updateGeometry(self)
		font = {'size'   : 10}

		rc('font', **font)


class DynamicMplCanvas(MyMplCanvas):
	"""A canvas that updates itself every second with a new plot."""

	def __init__(self, device, *args, **kwargs):
		self.device = device
		MyMplCanvas.__init__(self, *args, **kwargs)
		timer = QtCore.QTimer(self)
		timer.timeout.connect(self.update_figure)
		timer.start(1000)
		self.data = []

	def compute_initial_figure(self):
		self.axes.plot(range(len(self.device.getFrame().getReadings()))
				, self.device.getFrame().getReadings(), 'r')

	def update_figure(self):
		# Build a list of 4 random integers between 0 and 10 (both inclusive)
		if(self.device.getFrame().getReadings() is not None):
			self.data.append(self.device.getFrame().getReadings())
			self.axes.plot(self.data)
			self.axes.set_xlabel("Data Point", fontsize = 10)
			
			if(self.device.getFrame().getYLabel() is not None and
						len(self.device.getFrame().getUnits()) is not 0):
				self.axes.set_ylabel(self.device.getFrame().getYLabel()+" ("+
							self.device.getFrame().getUnits()[0]+")", fontsize = 10)
			elif(self.device.getFrame().getYLabel() is not None and
						len(self.device.getFrame().getCustomUnits()) is not 0):
				self.axes.set_ylabel(self.device.getFrame().getYLabel()+" ("+
							self.device.getFrame().getCustomUnits()+")", fontsize = 10)
			

			self.draw()

# qApp = QtGui.QApplication(sys.argv)

# aw = ApplicationWindow()
# aw.setWindowTitle("%s" % progname)
#aw.show()
#sys.exit(qApp.exec_())
#qApp.exec_()