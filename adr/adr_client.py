# Copyright (C) 2015  Chris Wilen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import matplotlib as mpl
import matplotlib.dates
mpl.use('TkAgg')
import pylab, numpy
import datetime, struct
from dateutil import tz
import Tkinter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
import labrad
from labrad import units
from labrad.server import (inlineCallbacks, returnValue)
from dataChest import dataChest
from dateStamp import dateStamp
from twisted.internet import tksupport, reactor
import os, time

class EntryWithAlert(Tkinter.Entry):
    """Inherited from the Tkinter Entry widget, this just turns red when a limit is reached"""
    def __init__(self, *args, **kwargs):
        self.upper_limit = kwargs.pop('upper_limit',False)
        self.lower_limit = kwargs.pop('lower_limit',False)
        self.variable = kwargs['textvariable']
        self.variable.trace('w',self.callback)
        Tkinter.Entry.__init__(self,*args,**kwargs)
        self.naturalBGColor = self.cget('disabledbackground')
    def setUpperLimit(self,limit):
        self.upper_limit = limit
    def setLowerLimit(self,limit):
        self.lower_limit = limit
    def callback(self,*dummy):
        if self.upper_limit != False or self.lower_limit != False:
            x = self.variable.get()
            if x == '' or x == 'PS OFF' or float(x) > float(self.upper_limit) or float(x) < float(self.lower_limit):
                self.configure(disabledbackground='red')
            else:
                self.configure(disabledbackground=self.naturalBGColor)

class LogBox(Tkinter.Text):
    """This class inherits a Tkinter Text widget to make a simple log box.  It will log an entry,
    and set the color to red if alert is set to True.  A time stamp is automatically added."""
    def __init__(self, *args, **kwargs):
        Tkinter.Text.__init__(self,*args,**kwargs)
        self.tag_config("redAlert", background="red")
        self.configure(state=Tkinter.DISABLED)
    def log(self, message, alert=False):
        self.configure(state=Tkinter.NORMAL)
        self.insert(1.0,message+'\n')
        if alert: self.tag_add("redAlert", '1.0', '1.end')
        self.configure(state=Tkinter.DISABLED)
    def clear(self):
        self.configure(state=Tkinter.NORMAL)
        self.delete(1.0,Tkinter.END)
        self.configure(state=Tkinter.DISABLED)


class ADRController(object):#Tkinter.Tk):
    """Provides a GUI for the ADRServer"""
    name = 'ADR Controller GUI'
    ID = 6116

    def __init__(self,parent):
        #Tkinter.Tk.__init__(self,parent)
        self.parent = parent
        self.selectedADR = None
        self.regulating = False
        #initialize and start measurement loop
        self.connect()
    @inlineCallbacks
    def connect(self,cxn=None):
        """Connects to labrad, loads the last 20 log messages, and starts listening for messages from the adr server."""
        if cxn == None:
            #make an asynchronous connection to LabRAD
            from labrad.wrappers import connectAsync
            self.cxn = yield connectAsync(name = self.name)
        else:self.cxn = cxn
        yield self.initializeWindow()
        self.startListening()
    @inlineCallbacks
    def correctServer(self,servId):
        try:
            id = yield self.cxn['ADR3'].ID
            returnValue( id == servId )
        except:
            returnValue( False )
    @inlineCallbacks
    def startListening(self):
        """The ADR Server sends out named messages every time the state is changed, the log is updated, or magging or regulation cycles complete.  This function starts the listeners for them.  Note: We used named messages instead of Signals because Signals are registered directly with the server instead of the manager (like named messages), so if the adr server disconnects and reconnects, the signals will no longer be sent here."""
        mgr = self.cxn.manager
        # example of Signal processing:
        # server = self.cxn[self.selectedADR]
        # update_state = lambda c, payload: self.updateInterface()
        # yield server.signal_state_changed(self.ID)
        # yield server.addListener(listener = update_state, source=None,ID=self.ID)

        # state update (only if
        update_state = lambda c, (s,payload): self.updateInterface() \
                if self.correctServer(s) else -1
        self.cxn._cxn.addListener(update_state, source=mgr.ID, ID=101)
        yield mgr.subscribe_to_named_message('State Changed', 101, True)
        # log update
        update_log = lambda c, (s,(m,a)): self.updateLog(m,a) \
                if self.correctServer(s) else -1
        self.cxn._cxn.addListener(update_log, source=mgr.ID, ID=102)
        yield mgr.subscribe_to_named_message('Log Changed', 102, True)
        # magging up stopped
        mag_stop = lambda c, (s,payload): self.magUpStopped() \
                if self.correctServer(s) else -1
        self.cxn._cxn.addListener(mag_stop, source=mgr.ID, ID=103)
        yield mgr.subscribe_to_named_message('MagUp Stopped', 103, True)
        # regulation stopped
        reg_stop = lambda c, (s,payload): self.regulationStopped() \
                if self.correctServer(s) else -1
        self.cxn._cxn.addListener(reg_stop, source=mgr.ID, ID=104)
        yield mgr.subscribe_to_named_message('Regulation Stopped', 104, True)
        # magging up started
        mag_start = lambda c, (s,payload): self.magUpStarted() \
                if self.correctServer(s) else -1
        self.cxn._cxn.addListener(mag_start, source=mgr.ID, ID=105)
        yield mgr.subscribe_to_named_message('MagUp Started', 105, True)
        # regulation started
        reg_start = lambda c, (s,payload): self.regulationStarted() \
                if self.correctServer(s) else -1
        self.cxn._cxn.addListener(reg_start, source=mgr.ID, ID=106)
        yield mgr.subscribe_to_named_message('Regulation Started', 106, True)
        # servers starting and stopping
        serv_conn_func = lambda c, (s, payload): self.populateADRSelectMenu()
        serv_disconn_func = lambda c, (s, payload): self.populateADRSelectMenu()
        self.cxn._cxn.addListener(serv_conn_func, source=mgr.ID, ID=107)
        self.cxn._cxn.addListener(serv_disconn_func, source=mgr.ID, ID=108)
        yield mgr.subscribe_to_named_message('Server Connect', 107, True)
        yield mgr.subscribe_to_named_message('Server Disconnect', 108, True)
    def initializeWindow(self):
        """Creates the GUI."""
        root = self.parent
        #set up window
        root.wm_title('ADR Magnet Controller')
        root.title('ADR Controller')
        w, h = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry("%dx%d+0+0" % (w/2, 0.9*h))
        #error/message box log
        self.log = LogBox(master=root, height=5)
        self.log.pack(side=Tkinter.TOP, fill=Tkinter.X)
        addToLogFrame = Tkinter.Frame(root)
        addToLogFrame.pack(side=Tkinter.TOP, fill=Tkinter.X)
        addToLogButton = Tkinter.Button(addToLogFrame, text='Add', command=self.addToLog)
        addToLogButton.pack(side=Tkinter.RIGHT)
        self.addToLogField = Tkinter.Text(addToLogFrame,height=1)
        self.addToLogField.pack(side=Tkinter.RIGHT, fill=Tkinter.X)
        # instrument statuses
        self.instrumentStatusFrame = Tkinter.Frame(root)
        self.instrumentStatusFrame.pack(side=Tkinter.TOP, fill=Tkinter.X)
        # temp plot
        self.fig = pylab.figure()
        self.ax = self.fig.add_subplot(111)
        #self.ax2 = self.ax.twinx()
        self.ax.set_title('Realtime Temperature Readout\n\n\n')
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Temparture [K]')
        self.stage60K, = self.ax.plot_date([],[],'-')
        self.stage03K, = self.ax.plot_date([],[],'-')
        self.stageGGG, = self.ax.plot_date([],[],'-')
        self.stageFAA, = self.ax.plot_date([],[],'-')
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.show()
        self.canvas.get_tk_widget().pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=1)
        #temp plot toolbar at bottom
        self.toolbar = NavigationToolbar2TkAgg( self.canvas, root )
        self.toolbar.update()
        #self.toolbar.pack(side=Tkinter.BOTTOM, fill=Tkinter.X)
        self.canvas._tkcanvas.pack(side=Tkinter.TOP, fill=Tkinter.BOTH, expand=1)
        #row of controls beneath temp plot
        tempAndADRControlFrame = Tkinter.Frame(root)
        tempAndADRControlFrame.pack(side=Tkinter.TOP, fill=Tkinter.X)
        # menu to select ADR
        self.adrSelect = Tkinter.StringVar(root)
        self.adrSelect.set('')
        self.adrSelect.trace('w',self.changeFridge)
        self.adrSelectWidget = Tkinter.OptionMenu(tempAndADRControlFrame,self.adrSelect,'')
        self.adrSelectWidget.grid(row=0, column=1, sticky=Tkinter.W)
        self.populateADRSelectMenu()
        #which temp plots should I show? (checkboxes)
        tempSelectFrameHolder = Tkinter.Frame(tempAndADRControlFrame)
        tempSelectFrameHolder.grid(row=0, column=2, sticky=Tkinter.W+Tkinter.E) # pack(side=Tkinter.LEFT)
        tempSelectFrame = Tkinter.Frame(tempSelectFrameHolder)
        tempSelectFrame.pack()
        tempAndADRControlFrame.columnconfigure(2, weight=1)
        self.t60K = Tkinter.IntVar()
        self.t3K = Tkinter.IntVar()
        self.tGGG = Tkinter.IntVar()
        self.tFAA = Tkinter.IntVar()
        self.t60K.set(0)
        self.t3K.set(1)
        self.tGGG.set(0)
        self.tFAA.set(1)
        t1checkbox = Tkinter.Checkbutton(tempSelectFrame, text = '60K Stage', variable=self.t60K, fg='blue')
        t1checkbox.pack(side=Tkinter.LEFT)
        t2checkbox = Tkinter.Checkbutton(tempSelectFrame, text = '3K Stage', variable=self.t3K, fg='forest green')
        t2checkbox.pack(side=Tkinter.LEFT)
        t3checkbox = Tkinter.Checkbutton(tempSelectFrame, text = '1K Stage (GGG)', variable=self.tGGG, fg='red')
        t3checkbox.pack(side=Tkinter.LEFT)
        t4checkbox = Tkinter.Checkbutton(tempSelectFrame, text = '50mK Stage (FAA)', variable=self.tFAA, fg='dark turquoise')
        t4checkbox.pack(side=Tkinter.LEFT)
        # scale to adjust time shown in temp plot
        wScaleOptions = ('10 minutes','1 hour','6 hours','24 hours','All')
        self.wScale = Tkinter.StringVar(root)
        self.wScale.set(wScaleOptions[1])
        apply(Tkinter.OptionMenu,(tempAndADRControlFrame,self.wScale)+wScaleOptions).grid(row=0, column=3, sticky=Tkinter.E) # pack(side=Tkinter.RIGHT)
        self.wScale.trace('w',self.updatePlot)
        # refresh instruments button
        refreshInstrButton = Tkinter.Button(root, text='Refresh Instruments', command=self.refreshInstruments)
        refreshInstrButton.pack(side=Tkinter.TOP)
        # start/stop compressor button
        self.compressorButton = Tkinter.Button(root, text='Start Compressor', command=self.startCompressor)
        self.compressorButton.pack(side=Tkinter.TOP)
        self.compressorButton.configure(state=Tkinter.DISABLED)
        #frame for mag up and regulate controls
        magControlsFrame = Tkinter.Frame(root)
        magControlsFrame.pack(side=Tkinter.TOP)
        #heat switch buttons
        self.HSCloseButton = Tkinter.Button(master=magControlsFrame, text='Close HS', command=self.closeHeatSwitch)
        self.HSCloseButton.pack(side=Tkinter.LEFT)
        self.HSOpenButton = Tkinter.Button(master=magControlsFrame, text='Open HS', command=self.openHeatSwitch)
        self.HSOpenButton.pack(side=Tkinter.LEFT)
        self.HSCloseButton.configure(state=Tkinter.DISABLED)
        self.HSOpenButton.configure(state=Tkinter.DISABLED)
        #mag up button
        self.magUpButton = Tkinter.Button(master=magControlsFrame, text='Mag Up', command=self.magUp)
        self.magUpButton.pack(side=Tkinter.LEFT)
        self.magUpButton.configure(state=Tkinter.DISABLED)
        #regulate button and temp field
        self.regulateButton = Tkinter.Button(master=magControlsFrame, text='Regulate', command=self.regulate)
        self.regulateButton.pack(side=Tkinter.LEFT)
        self.regulateButton.configure(state=Tkinter.DISABLED)
        Tkinter.Label(magControlsFrame, text=" at ").pack(side=Tkinter.LEFT)
        self.regulationTemp = Tkinter.DoubleVar()
        self.regulationTemp.set(0.1)
        self.regulationTemp.trace('w',self.changeRegTemp)
        self.regulateTempField = Tkinter.Entry(magControlsFrame, textvariable=self.regulationTemp)
        self.regulateTempField.pack(side=Tkinter.LEFT)
        Tkinter.Label(magControlsFrame, text="K").pack(side=Tkinter.LEFT)
        #shows current values for backEMF, current, voltage
        monitorFrame = Tkinter.Frame(root)
        monitorFrame.pack(side=Tkinter.TOP)
        self.currentBackEMF = Tkinter.StringVar() #current as in now, not as in amps
        self.currentI = Tkinter.StringVar()
        self.currentV = Tkinter.StringVar()
        Tkinter.Label(monitorFrame, text="Back EMF = ").pack(side=Tkinter.LEFT)
        self.backEMFField = EntryWithAlert(monitorFrame, textvariable=self.currentBackEMF, state=Tkinter.DISABLED)
        self.backEMFField.pack(side=Tkinter.LEFT)
        Tkinter.Label(monitorFrame, text="(V)   I = ").pack(side=Tkinter.LEFT)
        self.currentIField = EntryWithAlert(monitorFrame, textvariable=self.currentI, state=Tkinter.DISABLED)
        self.currentIField.pack(side=Tkinter.LEFT)
        Tkinter.Label(monitorFrame, text="(A)   V = ").pack(side=Tkinter.LEFT)
        self.currentVField = EntryWithAlert(monitorFrame, textvariable=self.currentV, state=Tkinter.DISABLED)
        self.currentVField.pack(side=Tkinter.LEFT)
        Tkinter.Label(monitorFrame, text="(V)").pack(side=Tkinter.LEFT)
        self.fig.tight_layout()
        self.setFieldLimits()
        root.protocol("WM_DELETE_WINDOW", self._quit) #X BUTTON
    def setFieldLimits(self):
        adrSettingsPath = yield self.cxn[self.selectedADR].get_settings_path()
        reg = self.cxn.registry
        reg.cd(adrSettingsPath)
        try: magVLimit = yield reg.get('magnet_voltage_limit')
        except Exception as e: magVLimit = 0.1
        try: PSILimit = yield reg.get('current_limit')
        except Exception as e: PSILimit = 9
        try: PSVLimit = yield reg.get('voltage_limit')
        except Exception as e: PSVLimit = 2
        self.backEMFField.setUpperLimit(magVLimit)
        self.currentIField.setUpperLimit(PSILimit)
        self.currentVField.setUpperLimit(PSVLimit)
    def closeHeatSwitch(self):
        self.cxn[self.selectedADR].close_heat_switch()
    def openHeatSwitch(self):
        self.cxn[self.selectedADR].open_heat_switch()
    @inlineCallbacks
    def populateADRSelectMenu(self):
        """This should be called by listeners for servers (dis)connecting.
        It updates the menu of ADRs from which one can select."""
        runningServers = yield self.cxn.manager.servers()
        runningADRs = [name for (_,name) in runningServers if 'ADR' in name and len(name)==4]
        self.adrSelectWidget['menu'].delete(0,'end')
        for adrServerName in runningADRs:
            self.adrSelectWidget['menu'].add_command(label=adrServerName, command=Tkinter._setit(self.adrSelect,adrServerName))
        if self.selectedADR in runningADRs:
            self.adrSelect.set(self.selectedADR)
        else:
            try:
                self.adrSelect.set(runningADRs[0])
            except IndexError as e:
                self.resetButtons()
                self.selectedADR = ''
            except Exception as e: print e
    def resetButtons(self):
        self.HSCloseButton.configure(state=Tkinter.DISABLED)
        self.HSOpenButton.configure(state=Tkinter.DISABLED)
        self.magUpButton.configure(state=Tkinter.DISABLED)
        self.regulateButton.configure(state=Tkinter.DISABLED)
        self.compressorButton.configure(state=Tkinter.DISABLED)
    @inlineCallbacks
    def changeFridge(self,*args):
        """Select which ADR you want to operate on.  Called when select ADR menu is changed."""
        self.selectedADR = self.adrSelect.get()
        # clear temps plot
        self.stage60K.set_xdata([])
        self.stage60K.set_ydata([])
        self.stage03K.set_xdata([])
        self.stage03K.set_ydata([])
        self.stageGGG.set_xdata([])
        self.stageGGG.set_ydata([])
        self.stageFAA.set_xdata([])
        self.stageFAA.set_ydata([])
        # load saved temp data
        # We have to sleep for 0.5s here because it seems like it takes
        # a moment for the connected server to register in self.cxn, even
        # though all this starts  because a message is received saying it
        # is connected :\
        time.sleep(0.5)
        startDateTime = yield self.cxn[self.selectedADR].get_start_datetime()
        try:
            tempDataChest = dataChest(['ADR Logs'])
            tempDataChest.cd(self.selectedADR)
            ds = dateStamp()
            dset = '%s_temperatures'%ds.dateStamp(startDateTime.isoformat())
            tempDataChest.openDataset(dset)
            
            n = tempDataChest.getNumRows()
            pastTempData = tempDataChest.getData(max(0,n-6*60*60), ) # load approximately the last 6 hours of data
            for newRow in pastTempData:
                # change utc time to local
                utc = newRow[0]
                utc = datetime.datetime.utcfromtimestamp(utc) # for float
                utc = utc.replace(tzinfo=tz.tzutc())
                newRow[0] = mpl.dates.date2num(utc)
                # add old data from file into plot
                self.stage60K.set_xdata(numpy.append(newRow[0],self.stage60K.get_xdata()))
                self.stage60K.set_ydata(numpy.append(newRow[1],self.stage60K.get_ydata()))
                self.stage03K.set_xdata(numpy.append(newRow[0],self.stage03K.get_xdata()))
                self.stage03K.set_ydata(numpy.append(newRow[2],self.stage03K.get_ydata()))
                self.stageGGG.set_xdata(numpy.append(newRow[0],self.stageGGG.get_xdata()))
                self.stageGGG.set_ydata(numpy.append(newRow[3],self.stageGGG.get_ydata()))
                self.stageFAA.set_xdata(numpy.append(newRow[0],self.stageFAA.get_xdata()))
                self.stageFAA.set_ydata(numpy.append(newRow[4],self.stageFAA.get_ydata()))
        except IOError: print 'temp file not created yet?' # file not created yet if first time opened
        self.updatePlot()
        # clear and reload log
        self.log.clear()
        logMessages = yield self.cxn[self.selectedADR].get_log(20) #only load last 20 messages
        for (m,a) in logMessages:
            self.updateLog(m,a)
        # update instrument status stuff: delete old, create new
        for widget in self.instrumentStatusFrame.winfo_children():
            widget.destroy()
        returnStatus = yield self.cxn[self.selectedADR].get_instrument_state()
        self.instrumentStatuses = {}
        for name,status in returnStatus:
            self.instrumentStatuses[name] = Tkinter.Label(self.instrumentStatusFrame,text=name,relief=Tkinter.RIDGE,bg='gray70')
            self.instrumentStatuses[name].pack(side=Tkinter.LEFT,expand=True,fill=Tkinter.X)
        # update field limits and button statuses
        self.setFieldLimits()
        self.magUpButton.configure(state=Tkinter.NORMAL)
        self.regulateButton.configure(state=Tkinter.NORMAL)
        self.compressorButton.configure(state=Tkinter.DISABLED)
        mUp = yield self.cxn[self.selectedADR].get_state_var('maggingUp')
        reg = yield self.cxn[self.selectedADR].get_state_var('regulating')
        if mUp:
            self.magUpButton.configure(text='Stop Magging Up', command=self.cancelMagUp)
            self.regulateButton.configure(state=Tkinter.DISABLED)
        if reg:
            self.regulateButton.configure(text='Stop Regulating', command=self.cancelRegulate)
            self.magUpButton.configure(state=Tkinter.DISABLED)
        # update heat switch buttons
        HSAvailable = yield self.cxn[self.selectedADR].get_instrument_state(['Heat Switch'])
        if HSAvailable[0][1][0]:
            self.HSCloseButton.configure(state=Tkinter.NORMAL)
            self.HSOpenButton.configure(state=Tkinter.NORMAL)
        else:
            self.HSCloseButton.configure(state=Tkinter.DISABLED)
            self.HSOpenButton.configure(state=Tkinter.DISABLED)
        # refresh interface
        self.updateInterface()
    def refreshInstruments(self):
        self.cxn[self.selectedADR].refresh_instruments()
    @inlineCallbacks
    def updateInterface(self):
        """ update interface to reflect system state """
        p = self.cxn[self.selectedADR].packet()
        p.magnetv().pscurrent().psvoltage()
        p.time()
        p.temperatures()
        p.get_state_var('CompressorStatus')
        p.get_instrument_state()
        state = yield p.send()
        # change instrument statuses
        for name,status in state['get_instrument_state']:
            if status[0] == False: color = 'red3'
            elif status[1] == False: color = 'orange3'
            elif status[1] == True: color = 'green3'
            else: color = 'gray70'
            self.instrumentStatuses[name].config(bg=color)
        # enable/disable mag up/reg buttons depending on instrument status
        # disable if power supply or magnet voltage sensor is down
        self.lastStateM = self.magUpButton.cget('state')
        self.lastStateR = self.regulateButton.cget('state')
        # &&&
        # change compressor button
        if state['get_state_var'] == True:
            self.compressorButton.configure(text='Stop Compressor', command=self.stopCompressor, state=Tkinter.NORMAL)
        elif state['get_state_var'] == False:
            self.compressorButton.configure(text='Start Compressor', command=self.startCompressor, state=Tkinter.NORMAL)
        else: self.compressorButton.configure(state=Tkinter.DISABLED)
        # update current, voltage fields
        temps = {}
        stages = ('T_60K','T_3K','T_GGG','T_FAA')
        for i in range(len(stages)):
            temps[stages[i]] = state['temperatures'][i]
            #if temps[stages[i]] == 'nan': temps[stages[i]] = numpy.nan
        if numpy.isnan(state['magnetv']['V']): emf = 'ERR'
        else: emf = "{0:.3f}".format(state['magnetv']['V'])
        if numpy.isnan(state['pscurrent']['A']): psI = 'PS OFF'
        else: psI = "{0:.3f}".format(state['pscurrent']['A'])
        if numpy.isnan(state['psvoltage']['V']): psV = 'PS OFF'
        else: psV = "{0:.3f}".format(state['psvoltage']['V'])
        self.currentBackEMF.set( emf )
        self.currentI.set( psI )
        self.currentV.set( psV )
        # update plot:
        # change data to plot
        self.stage60K.set_xdata(numpy.append(self.stage60K.get_xdata(),mpl.dates.date2num(state['time'])))
        self.stage60K.set_ydata(numpy.append(self.stage60K.get_ydata(),temps['T_60K']['K']))
        self.stage03K.set_xdata(numpy.append(self.stage03K.get_xdata(),mpl.dates.date2num(state['time'])))
        self.stage03K.set_ydata(numpy.append(self.stage03K.get_ydata(),temps['T_3K']['K']))
        self.stageGGG.set_xdata(numpy.append(self.stageGGG.get_xdata(),mpl.dates.date2num(state['time'])))
        self.stageGGG.set_ydata(numpy.append(self.stageGGG.get_ydata(),temps['T_GGG']['K']))
        self.stageFAA.set_xdata(numpy.append(self.stageFAA.get_xdata(),mpl.dates.date2num(state['time'])))
        self.stageFAA.set_ydata(numpy.append(self.stageFAA.get_ydata(),temps['T_FAA']['K']))
        #update plot
        self.updatePlot()
        # update legend
        labelOrder = ['T_60K','T_3K','T_GGG','T_FAA']
        lines = [self.stage60K,self.stage03K,self.stageGGG,self.stageFAA]
        labels = [l.strip('T_')+' ['+"{0:.3f}".format(temps[l]['K'])+'K]' for l in labelOrder]
        labels = [s.replace('1.#QOK','OoR') for s in labels]
        #self.ax.legend(lines,labels,loc=0)#,bbox_to_anchor=(1.01, 1)) #legend in upper right
        self.ax.legend(lines,labels,bbox_to_anchor=(0., 1.02, 1., .102), loc=3,
           ncol=4, mode="expand", borderaxespad=0.) #legend on top (if not using this, delete \n in title)
    def updatePlot(self,*args):
        """This just updates the limits on the plot.  We put it in a separate function so
        it can be called when the time selection menu is changed."""
        # set x limits
        timeDisplayOptions = {'10 minutes':10,'1 hour':60,'6 hours':6*60,'24 hours':24*60,'All':0}
        try:
            lastDatetime = mpl.dates.num2date(self.stage60K.get_xdata()[-1])
            firstDatetime = mpl.dates.num2date(self.stage60K.get_xdata()[0])
        except IndexError: # no data yet
            now = datetime.datetime.utcnow().toordinal()
            firstDatetime = mpl.dates.num2date(now)
            lastDatetime = firstDatetime
        xMin = lastDatetime-datetime.timedelta(minutes=timeDisplayOptions[self.wScale.get()])
        xMin = max([ firstDatetime, xMin ])
        if self.wScale.get() == 'All': xMin = firstDatetime
        xMinIndex = numpy.searchsorted( self.stage60K.get_xdata(), mpl.dates.date2num(xMin) )
        # rescale axes, with the x being scaled by the slider
        if self.toolbar._active == 'HOME' or self.toolbar._active == None:
            ymin,ymax = 10000000, -10000000
            lineAndVar = {self.stage60K:self.t60K, self.stage03K:self.t3K, self.stageGGG:self.tGGG, self.stageFAA:self.tFAA}
            if len(self.stage60K.get_xdata())>1:
                for line in lineAndVar.keys():
                    if lineAndVar[line].get() == 0: line.set_visible(False)
                    else:
                        line.set_visible(True)
                        ydata = line.get_ydata()[xMinIndex:-1]
                        try:
                            ymin = min(ymin, numpy.nanmin(ydata))
                            ymax = max(ymax, numpy.nanmax(ydata))
                        except ValueError as e: pass
                self.ax.set_xlim(xMin,lastDatetime)
                self.ax.set_ylim(ymin - (ymax-ymin)/10, ymax + (ymax-ymin)/10)
                hfmt = mpl.dates.DateFormatter('%H:%M:%S', tz=tz.tzlocal())
                self.ax.xaxis.set_major_formatter(hfmt)
                self.fig.autofmt_xdate()
                self.fig.tight_layout()
        #draw
        self.canvas.draw()
    def updateLog(self,message=None,alert=False):
        if message:
            self.log.log(message,alert)
    def addToLog(self):
        text = str( self.addToLogField.get(1.0, Tkinter.END) )
        try:
            self.cxn[self.selectedADR].add_to_log(text)
            self.addToLogField.delete(1.0, Tkinter.END)
        except Exception as e: pass
    def startCompressor(self):
        self.cxn[self.selectedADR].start_compressor()
    def stopCompressor(self):
        self.cxn[self.selectedADR].stop_compressor()
    def magUp(self):
        self.cxn[self.selectedADR].mag_up()
    def magUpStarted(self):
        self.magUpButton.configure(text='Stop Magging Up', command=self.cancelMagUp)
        self.regulateButton.configure(state=Tkinter.DISABLED)
    def cancelMagUp(self):
        self.cxn[self.selectedADR].cancel_mag_up()
    def magUpStopped(self):
        self.magUpButton.configure(text='Mag Up', command=self.magUp)
        self.regulateButton.configure(state=Tkinter.NORMAL)
    def regulate(self):
        T_target = float(self.regulationTemp.get())
        self.cxn[self.selectedADR].regulate(T_target)
    def changeRegTemp(self, *args):
        if self.regulating == True:
            T_target = float(self.regulationTemp.get())
            print self.regulationTemp.get(),T_target
            self.cxn[self.selectedADR].regulate(T_target)
    def regulationStarted(self):
        self.regulateButton.configure(text='Stop Regulating', command=self.cancelRegulate)
        self.magUpButton.configure(state=Tkinter.DISABLED)
        self.regulating = True
    def cancelRegulate(self):
        self.cxn[self.selectedADR].cancel_regulation()
    def regulationStopped(self):
        self.regulateButton.configure(text='Regulate', command=self.regulate)
        self.magUpButton.configure(state=Tkinter.NORMAL)
        self.regulating = False

    def _quit(self):
        """ called when the window is closed."""
        self.parent.quit()     # stops mainloop
        self.parent.destroy()  # this is necessary on Windows to prevent
                               # Fatal Python Error: PyEval_RestoreThread: NULL tstate
        reactor.stop()

if __name__ == "__main__":
    mstr = Tkinter.Tk()
    tksupport.install(mstr)
    app = ADRController(mstr)
    reactor.run()
