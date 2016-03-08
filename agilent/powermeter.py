from __future__ import division
from drivepy.base.powermeter import BasePowerMeter, CommError, PowerMeterLibraryError
import drivepy.visaconnection as visaconnection
import math
DEFAULT_AVERAGING_TIME = 100    # ms
AVERAGING_TIME_MAX_MODE = 20    # ms

class PowerMeter(BasePowerMeter):
    """ Creates a power meter object for the Agilent 8163A/B power meter via GPIB """
    def __init__(self, addr = "GPIB::20"):
        self._conn=VisaConnection(addr)
        self._conn.write("*RST")
        # make sure that the refernece is not used
        self._conn.write("SENS1:CHAN1:POW:REF:STATE 0")
        # clear the error queue
        self._conn.write("*CLS")
        # turn auto range on
        self._conn.write("SENS1:CHAN1:POW:RANGE:AUTO 1")
        # change the power unit to Watts
        self._conn.write("SENS1:CHAN1:POW:UNIT W")
        # set the default averaging time
        self.tau = None
        self._setTau(DEFAULT_AVERAGING_TIME)
        # turn continuous measuring on
        self._conn.write("INIT1:CHAN1:CONT 1")

    def readPower(self, tau=DEFAULT_AVERAGING_TIME, mode="mean"):
        """ Read the power using specified averaging time and either max or averaging mode """
        if mode == 'mean' or tau <= AVERAGING_TIME_MAX_MODE:
            self._setTau(tau)
            return self._readPower()
        elif mode == "max":
            n = int(math.ceil(tau/AVERAGING_TIME_MAX_MODE))
            self._setTau(AVERAGING_TIME_MAX_MODE)
            return max([self._readPower() for i in range(n)])
    
    def _setTau(self, tau):
        if not tau == self.tau:
            self._conn.write("SENS1:CHAN1:POW:ATIME %f"%(tau/1000))
            self.tau = tau
    
    def _readPower(self):
        readStr=self._conn.readQuery("READ1:CHAN1:POW?")
        return float(readStr)
        
class VisaConnection(visaconnection.VisaConnection):
    """ Abstraction of the VISA connection for consistency between implementation of instrument classes """
    def __init__(self,addr):
        super(VisaConnection,self).__init__(addr)  
    def __del__(self):
        self.write(":INIT:CONT 1")