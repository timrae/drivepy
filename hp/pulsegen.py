from __future__ import division
from drivepy import visaconnection
from PyQt4 import QtGui
from time import sleep

class PulseGenerator(object):
    """ Class for the 8114A Pulse Generator"""
    def __init__(self,addr="GPIB::14"):
        self._pg=VisaConnection(addr)
        self.current=0
    def setCurrent(self,current,vComp=None):
        newCurrent,status=QtGui.QInputDialog.getDouble(None,"Enter the measured value of the current (mA): ", "Set Current",current*1000,0,inf,3)
        self.current=newCurrent/1000

    def measure(self):
        v=float(self._pg.read("VOLT:HIGH?"))
        return (v,self.current)
 
    def setOutputState(self,state):
        """ Turns the SMU on or off depending on state. state can be ('ON'/True/1), ('OFF',False,0)"""
        if state=="ON" or state==1 or state==True:
            self._pg.write(":OUTP ON")
        elif state=="OFF" or state==0 or state==False:
            self._pg.write(":OUTP OFF")
        else:
            raise TypeError,"Type error setting state of SMU. Examples of correct state are ('ON','OFF',True,0)"
        # wait for the output to finish switching.
        sleep(10e-3)
        # set the state so we can keep track of it
        self.state=state



class VisaConnection(visaconnection.VisaConnection):
    """ Abstraction of the VISA connection for consistency between implementation of instrument classes """
    def __init__(self,addr,t=5):
        super(VisaConnection,self).__init__(addr,t)  
    def __del__(self):
        self.write(":OUTP OFF")






