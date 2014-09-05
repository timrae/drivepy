from __future__ import division
from drivepy.keithley.dmm import DMM
from numpy import zeros, mean, max
import time
SENSITIVITY=1.489e-4    # 0.15mW/V
INSERTION_LOSS=.01  # assume 1% tap off from main fiber into power meter

class PowerMeter(object):
    """ Creates a power meter object for the Newfocus power meter connected to a DMM."""
    def __init__(self,gpibAddr=None):
        if gpibAddr==None:
            self.dmm=DMM()
        else:
            self.dmm=DMM(gpibAddr)
       
    def readPower(self,backgroundVoltage=0,n=1):
        """ routine to read a single power measurement """
        # V=self.dmm.measure()
        V=self.bestOfN(n)
        return self.voltageToPower(V-backgroundVoltage)

    def readPowerAuto(self,tau=200,timeout=10,mode="mean"):
        """ read power including automatic error handling """
        self.t0=time.time()
        # Automatically remeasure if there was a comm. error until timeout occurs
        while 1:
            try:
                power=self._readPowerAuto(tau,timeout,mode)
                break
            except CommError as e:
                if time.time()-self.t0 < timeout:
                    pass
                else:
                    # If timeout occurs, re-raise the (same) error
                    raise
        del self.t0
        return power

    def _readPowerAuto(self,tau,timeout,mode):
        """ use automatic ranging """
        # Hack to get something working
        self.dmm.setAuto()
        return self.readPower()

    def bestOfN(self,n):
        """ Hack to take best n readings in case of moving target """
        v=zeros((n,1))
        for idx in range(n):
            v[idx]=self.dmm.measure()
        return max(v)

        
    def voltageToPower(self,V):
        return max(V*SENSITIVITY/INSERTION_LOSS,0)

class CommError(Exception): pass
class PowerMeterLibraryError(Exception): pass