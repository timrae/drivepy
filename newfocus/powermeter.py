from __future__ import division
from drivepy.base.powermeter import BasePowerMeter
from drivepy.keithley.dmm import DMM
from numpy import zeros, mean, max
import time
SENSITIVITY=1.489e-4    # 0.15mW/V
INSERTION_LOSS=.01  # assume 1% tap off from main fiber into power meter

class PowerMeter(BasePowerMeter):
    """ Creates a power meter object for the Newfocus power meter connected to a DMM."""
    def __init__(self,gpibAddr=None):
        if gpibAddr==None:
            self.dmm=DMM()
        else:
            self.dmm=DMM(gpibAddr)

    def readPower(self, tau=200, mode="mean"):
        """ use automatic ranging """
        # Hack to get something working
        self.dmm.setAuto()
        V=self._bestOfN(n)
        return self._voltageToPower(V-backgroundVoltage)

    def _bestOfN(self,n):
        """ Hack to take best n readings in case of moving target """
        v=zeros((n,1))
        for idx in range(n):
            v[idx]=self.dmm.measure()
        return max(v)

    def _voltageToPower(self,V):
        return max(V*SENSITIVITY/INSERTION_LOSS,0)