import time
import numpy as np
import atsapi as ats

import labrad
from labrad.units import V

cxn = labrad.connect()
digitizer = cxn.ats_waveform_digitizer
digitizer.select_device("ATS1::1")

digitizer.configure_external_clocking()
digitizer.configure_trigger()
digitizer.configure_inputs(4*V)
digitizer.samples_per_record(512)
digitizer.records_per_buffer(10)
digitizer.number_of_records(100)
digitizer.configure_buffers()

t = np.linspace(0, 255, 256)
Omega = 30.028e6*2*np.pi
WA = np.cos(Omega * t)
WB = np.sin(Omega * t)
digitizer.add_demod_weights(WA, WB, "test")

start = time.time()
digitizer.acquire_data()
iqs = digitizer.get_iqs("test")
data = digitizer.get_records()
stop = time.time()
print('Executions time: %f seconds.' %(stop-start))