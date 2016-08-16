import smtplib
import MMail
import threading
import time
import sys
sys.dont_write_bytecode = True
#from email.mime.text import MIMEText

class MAlert:
    def __init__(self, dict,  devices, tele, refrate):
        # Configure all public variables
        self.dict = dict
        #print self.dict
        self.tele = tele
        self.devices = devices
        self.t1 = 0
        self.message = []
        self.refreshRateSec = refrate
        # Have the specified people been notified about the specific device?
        self.mailSent ={}
        # Keep running, this is false when settings are changed and a 
        # new NAlert instance is created. Setting this to false terminates
        # the thread.
        self.keepGoing = True
        # Keep track of which mail was sent
        for i in range(0, len(self.devices)):
            for y in range(0, len(self.devices[i].getFrame().getNicknames())):
                if(self.devices[i].getFrame().getNicknames()[y] is not None):
                   # print self.mailSent
                    self.mailSent[self.devices[i].getFrame().getTitle()+":"+self.devices[i].getFrame().getNicknames()[y]] = False
                    #print(len(self.mailSent))
    def begin(self):
        # This runs on its own thread
        self.deviceThread = threading.Thread(target = self.monitorReadings, args=[])
        # If the main thread stops, stop the child thread
        self.deviceThread.daemon = True
        # Start the thread
        self.deviceThread.start()
        self.keepGoing = True
    def monitorReadings(self):
        # The dictionary keys are in the format 'devicename:parametername' : '
        # for entry in self.dict:
            # print entry,":", self.dict[entry] 
       # print "MALERT dict", self.dict
        for i in range(len(self.devices)):
            for y, param in enumerate(self.devices[i].getFrame().getNicknames()):
                key = self.devices[i].getFrame().getTitle()+":"+param
                enabled, min, max, people = self.dict[key]
                min = self.toFloat(min)
                max = self.toFloat(max)
                if self.devices[i].getFrame().getReadings() != None:
                    reading = self.devices[i].getFrame().getReadings()[y]
                    #print "enabled: ", enabled
                    if(enabled):
                        #print key,self.dict[key]
                        if(min != None and min>reading):
                            print "MALERT reading below min ", min
                            self.devices[i].getFrame().setOutOfRange(key)
                            self.sendMail(self.devices[i], y, reading, people, min, max)
                            
                           # device.getFrame().setOutOfRange((True, y))
                        elif(max != None and max<reading):
                            #print max
                            print "MALERT reading above max", max
                            self.devices[i].getFrame().setOutOfRange(key)
                            self.sendMail(self.devices[i], y, reading, people, min, max) 
                            
                        else:
                            print key, "MALERT reading within range"
                            self.devices[i].getFrame().setInRange(key)    
                    else:
                        print key, "MALERT reading within disabled"
                        self.devices[i].getFrame().setInRange(key)
        if(self.keepGoing):
            threading.Timer(self.refreshRateSec, self.monitorReadings).start()
    def toFloat(self, val):
        try:
            return float(val)
        except:
            return None
            
    def stop(self):
        self.keepGoing = False

    def sendMail(self, device, y, reading, people, min, max):
        '''Send mail if the given amount of time has elapsed.'''
        
        HOURS_BETWEEN_EMAILS = 3
        elapsedHrs = (time.time()-self.t1)/3600
        key = device.getFrame().getTitle()+":"+device.getFrame().getNicknames()[y] 
        print people == ''
        if people != '':
            if(not self.mailSent[key]):
                self.message.append(("Time: "
                    +time.asctime( time.localtime(time.time()) )
                    +" | "+device.getFrame().getTitle()+"->"
                    + device.getFrame().getNicknames()[y] + ": "+
                    str(device.getFrame().getReadings()[y])+
                    device.getFrame().getUnits()[y] +
                    " | Range: "
                    +str(min) 
                    + device.getFrame().getUnits()[y]+
                    " - " +str(max)+
                    device.getFrame().getUnits()[y]+"."))
                
                self.mailSent[key] = True

            
            if(HOURS_BETWEEN_EMAILS<elapsedHrs):
                #print len([str(person).strip() for person in people.split(',')][0])
                if not len([str(person).strip() for person in people.split(',')][0]) == 0:
                    print "sending mail"
                    print self.message
                    success, address = self.tele.send_sms(
                        device.getFrame().getNicknames()[y], 
                                            str(self.message), 
                                            [str(person).strip() for person in people.split(',')],
                                            "labrad_physics")
                    print  [str(person).strip() for person in people.split(',')]
                    if (not success):
                        print("Couldn't send email to group: "+
                           str([str(person).strip() for person in people.split(',')])+" | "+str(success)+" "+str(address))
                    self.message = []
                    #self.mailSent = {}
                    for key in self.mailSent:
                        self.mailSent[key] = False
                    self.t1 = time.time()
    
