from __future__ import division
from drivepy.base.powermeter import BasePowerMeter, CommError, PowerMeterLibraryError
import visaconnection
DEFAULT_AVERAGING_TIME = 0.1    # 100ms

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
        self.tau = DEFAULT_AVERAGING_TIME
        self._conn.write("SENS1:CHAN1:POW:ATIME %f"%self.tau)
        # turn continuous measuring on
        self._conn.write("INIT1:CHAN1:CONT 1")

    def readPower(self, tau=DEFAULT_AVERAGING_TIME, mode="mean"):
        """ Read the power using specified averaging time and either max or averaging mode """
        if not tau == self.tau:
            self.tau = tau
            self._conn.write("SENS1:CHAN1:POW:ATIME %f"%self.tau)
        if mode == "max":
            raise NotImplementedError, "Max mode not currently supported"
            # use bestOfN() ? 
            # TODO: Also need to implement the VISA timeout and check Newfocus / Winspec devices
        return self._readPower()
    
    def _readPower(self):
        readStr=self._conn.readQuery("READ1:CHAN1:POW?")
        return float(readStr)
        
class VisaConnection(visaconnection.VisaConnection):
    """ Abstraction of the VISA connection for consistency between implementation of instrument classes """
    def __init__(self,addr):
        super(VisaConnection,self).__init__(addr)  
    def __del__(self):
        self.write(":INIT:CONT 1")