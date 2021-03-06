# Use at your own risk
  
"""
### BEGIN NODE INFO
[info]
name = SIM928_test
version = 1.1.0
description = 
  
[startup]
cmdline = %PYTHON% %FILE%
timeout = 20
  
[shutdown]
message = 987654321
timeout = 5
### END NODE INFO
"""

from twisted.internet.defer import inlineCallbacks, returnValue
from labrad.server import setting
from labrad.gpib import GPIBManagedServer
from labrad import units
from exceptions import ValueError

TC = "'end'" # Termination Character
LF = '\n' # Line Feed

class SIM928Server(GPIBManagedServer):
    name = 'SIM928_test'
    deviceName = 'STANFORD RESEARCH SYSTEMS SIM900'

    @inlineCallbacks   
    def write(self, c, slot_number, write_str):
        """A write method that addresses a particular slot
           in the SIM 900 mainframe. Connection with the
           instrument (slot) is closed after the message
           is sent."""
        dev = self.selectedDevice(c)
        yield dev.write("CONN "+str(slot_number)+","+TC+LF)
        yield dev.write("TERM LF"+LF)
        yield dev.write(write_str + LF)
        yield dev.write(TC)
        
    @inlineCallbacks   
    def query(self, c, slot_number, query_str):
        """A query method that addresses a particular slot
           in the SIM 900 mainframe. Connection with the
           instrument (slot) is closed after the query is
           finished."""
        dev = self.selectedDevice(c)
        yield dev.write("CONN "+str(slot_number)+","+TC+LF)
        yield dev.write("TERM LF"+LF)
        query_resp = yield dev.query(query_str + LF)
        yield dev.write(TC)
        returnValue(query_resp)

    def no_selection_msg(self):
        err_msg = "You must first select a slot for the SIM 928."
        return err_msg
        
    def slot_not_found_msg(self, slot_number):
        err_msg = "A SIM 928 on slot # %s was not found." % slot_number
        return err_msg
        
    @setting(8, 'Initialize Mainframe', returns = 'b')
    def initialize_mainframe(self, c):
        """Mainframe initialization method used for resetting
           the SIM 900 once it goes into an error state."""
        dev = self.selectedDevice(c)
        yield dev.write("*RST\n")
        yield dev.write("VERB 127\n")
        yield dev.write("CEOI ON\n")
        yield dev.write("EOIX ON\n")
        yield dev.write("TERM D,LF\n")
        
        for ii in range(0, 12):
            yield dev.write("BAUD "+str(ii)+",9600\n")
        
        yield dev.write("FLSH\n")
        yield dev.write("SRST\n")
        returnValue(True)
        
    @setting(9, 'Find Source', slot_number = 'i', returns = 'b')
    def find_source(self, c, slot_number):
        """Determines if a SIM 928 voltage source with the
           specified slot_number is present in the mainframe."""
        dev = self.selectedDevice(c)
        module_status = yield dev.query("CTCR?\n")
        module_status = '{0:b}'.format(int(module_status))[4:-1][::-1]
        module_status = [bool(int(char)) for char in module_status]
        for ii in range(0, len(module_status)):
            if slot_number == ii + 1:
                if module_status[ii]:
                    try:
                        idn_str = yield self.query(c, 
                                                   slot_number,
                                                   "*IDN?")
                    except:
                        self.initialize_mainframe(c)
                        idn_str = yield self.query(c, 
                                                   slot_number,
                                                   "*IDN?")
                    if 'SIM928' in idn_str:
                        returnValue(True)
        returnValue(False)

    @setting(10, 'Select Source', slot_number = 'i', returns = '')
    def select_source(self, c, slot_number):
        """Selects the SIM 928 voltage source you intend to
           communicate with."""
        source_found = yield self.find_source(c, slot_number)
        if source_found:
            c['slot_number'] = slot_number
        else:
            raise ValueError(self.slot_not_found_msg(slot_number))

    @setting(11, 'Get Voltage', returns = 'v[V]')
    def get_voltage(self, c):
        """Gets the SIM 928 voltage output value from the
           selected source."""
        voltage_error = True
        while voltage_error == True:
            voltage_error = False
            if 'slot_number' in c.keys():
                slot_number = c['slot_number']
                voltage = yield self.query(c,
                                               slot_number, 
                                               "VOLT?")
                try:
                    voltage = float(voltage)
                except(ValueError):
                    voltage_error = True
                    print 'error getting voltage from sim, got: \'' + str(voltage) + '\''
                    # print voltage
                    # old_voltage = voltage
                    # voltage = ''.join([i for i in voltage if (i.isdigit() or i == '-' or i == '.')])
                    # voltage = float(voltage)
                    # print ('The value ' + old_voltage + ' was returned by the SIM928, this value was automatically converted to ' + voltage + '.')
                
                if voltage_error == False:
                    value = voltage * units.V
            
        returnValue(value)
        
    @setting(12, 'Get Slot', returns = 'i')
    def get_slot(self, c):
        """Gets the slot_number of the selected SIM 928 source."""
        if 'slot_number' in c.keys():
            slot_number = c['slot_number']
            return slot_number
        else:
            raise ValueError(self.no_selection_msg())
           
        # returnValue(voltage * units.V)
        
    @setting(13, 'Set Voltage',
             voltage = 'v[V]', returns = '')
    def set_voltage(self, c, voltage):
        """Sets SIM 928 voltage for the selected source."""
        if 'slot_number' in c.keys():
            slot_number = c['slot_number']
            output_state = yield self.get_output_state(c)
            if not output_state:
                try:
                    yield self.set_output_state(c, True)
                except:
                    self.initialize_mainframe(c)
                    yield self.set_output_state(c, True)
            write_str = "VOLT "+ str(voltage['V'])
            try:
                yield self.write(c, slot_number, write_str)
            except:
                self.initialize_mainframe(c)
                yield self.write(c, slot_number, write_str)
        else:
            raise ValueError(self.no_selection_msg())

    @setting(14, 'Get Output State', returns = 'b')
    def get_output_state(self, c):
        """Gets SIM 928 voltage output state 
           for the selected slot number."""
        if 'slot_number' in c.keys():
            slot_number = c['slot_number']
            if 'output_state' not in c.keys():
                try:
                    output_state = yield self.query(c,
                                                    slot_number,
                                                    "EXON?")
                    output_state = bool(int(output_state))
                    c['output_state'] = output_state  
                except:
                    self.initialize_mainframe(c)
                    output_state = yield self.query(c,
                                                    slot_number,
                                                    "EXON?")
                    output_state = bool(int(output_state))
                    c['output_state'] = output_state  
        else:
            raise ValueError(self.no_selection_msg())
        returnValue(c['output_state'] )    

    @setting(15, 'Set Output State',
             output_on = 'b', returns = '')
    def set_output_state(self, c, output_on):
        """Sets SIM 928 voltage output state for 
           the selected slot number."""
        if 'slot_number' in c.keys():
            slot_number = c['slot_number']
            if output_on:
                try:
                    output_state = yield self.write(c, 
                                                    slot_number, 
                                                    "OPON")
                    c['output_state'] = True
                except:
                    self.initialize_mainframe(c)
                    output_state = yield self.write(c, 
                                                    slot_number, 
                                                    "OPON")
                    c['output_state'] = True
            else:
                try:
                    output_state = yield self.write(c,
                                                    slot_number,
                                                    "OPOF")
                    c['output_state'] = False
                except:
                    self.initialize_mainframe(c)
                    output_state = yield self.write(c,
                                                    slot_number,
                                                    "OPOF")
                    c['output_state'] = False
        else:
            raise ValueError(self.no_selection_msg())      

__server__ = SIM928Server()
  
if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
    
##### EXAMPLE #####
#   import labrad
#   from labrad import units
#   cxn = labrad.connect()
#   v1 = cxn.sim928
#   v1.select_device(0) # this argument depends on gpib address
#   v1.select_source(1) # slot number for chose mainframe
#   v1.set_voltage(0.5 * units.V)
#   v1.get_voltage() # returns 0.5 * V
#   v1.get_output_state() #True, turned on by default if voltage is set
#   v1.set_output_state(False)
#   v2 = cxn.sim928
#   v2.select_device(0)
#   v2.select_device(2) # chose another source with different slot num

