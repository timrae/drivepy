from __future__ import division
from drivepy import visaconnection
from time import sleep
NPLC=10 # Default integration time
class DMM(object):
    """ Class for the source measure unit which provides high level commands for setting and reading the current """
    def __init__(self,addr="GPIB::1",autoZero=True,disableScreen=False):
        self._dmm=VisaConnection(addr)
        self._dmm.write("*RST")
        self._dmm.write(":SYST:BEEP:STAT OFF")
        self._dmm.write(":CONF:VOLT:DC")
        if disableScreen:
            self._dmm.write("DISP:ENAB 0")
        if not autoZero:
            self._dmm.write(":SYST:AZER:STAT 0") # Turn off auto-zero to improve speed
        self._dmm.write(":SENS:VOLT:DC:NPLC "+str(NPLC))
        self._dmm.write(":SENS:VOLT:DC:RANG:UPP 0")
        self._dmm.write(":SENS:VOLT:DC:AVER:STAT 0")

    def measure(self):
        """ Returns measurement for configured measurement type"""
        readStr=self._dmm.readQuery(":READ?")
        return float(readStr)

    def setAuto(self):
        self._dmm.write(":SENS:VOLT:DC:RANG:AUTO 1")

class VisaConnection(visaconnection.VisaConnection):
    """ Abstraction of the VISA connection for consistency between implementation of instrument classes """
    def __init__(self,addr,t=None):
        super(VisaConnection,self).__init__(addr,t)  
    def __del__(self):
        self.write(":INIT:CONT 1")
        #self.write(":SYST:LOC") not working for some reason





