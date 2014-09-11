from __future__ import division
from drivepy import visaconnection
from time import sleep
NPLC=1 # Default integration time
class SMU(object):
    """ Class for the source measure unit which provides high level commands for setting and reading the current """
    def __init__(self,addr="GPIB::25",autoZero=True,disableScreen=False,defaultCurrent=50e-3, currRange=0.1):
        self._smu=VisaConnection(addr,defaultCurrent=defaultCurrent)
        self._smu.write("*RST")
        self._smu.write(":FORM:ELEM:SENS VOLT,CURR")
        if disableScreen:
            self._smu.write("DISP:ENAB 0")
        self.setCurrent(0)
        self.setBeepState(1)
        self.setOutputState(1)
        self.setBeepState(0)
        if not autoZero:
            self._smu.write(":SYST:AZER:STAT 0") # Turn off auto-zero to improve speed
        self._smu.write(":SENS:CURR:NPLC "+str(NPLC))
        self.setCurrRange(currRange)
    def setCurrent(self,setCurr,Vcomp=3.5):
        """ Sets the current and returns a voltage from SMU"""
        # Set source mode
        self._smu.write(":SOUR:FUNC CURR; :SOUR:CURR:MODE FIX")
        # Set current and range. Would be nice to set the range automatically based on supplied current
        self._smu.write(":SOUR:CURR:LEV "+str(setCurr)) 
        # Setup voltage measure function
        self._smu.write(':SENS:FUNC "VOLT";' + ":SENS:VOLT:PROT "+str(Vcomp)+"; :SENS:VOLT:RANG 10")

    def setCurrRange(self,range):
        self._smu.write(":SOUR:CURR:RANGE " + str(range))

    def measure(self):
        """ Returns (voltage,current) measurement tuple from SMU """
        assert self.state, "The SMU needs to be turned ON to make an ouput measurement"
        readStr=self._smu.readQuery(":READ?").split(',')
        return (float(readStr[0]),float(readStr[1]))
    def autoZeroOnce(self):
        """ This is a workaround to autozero the SMU. ':SYS:AZER:STAT ONCE' would be better but not working. 
        This autoZero command should be called more than every 10 minutes """
        self._smu.write(":SENS:CURR:NPLC "+str(2*NPLC))
        self._smu.write(":SENS:CURR:NPLC "+str(NPLC))

    def setBeepState(self,state):
        """ Enable or disable the beeper """
        if state=="ON" or state==1 or state==True:
            self._smu.write(":SYST:BEEP:STAT ON")
        elif state=="OFF" or state==0 or state==False:
            self._smu.write(":SYST:BEEP:STAT OFF")
        else:
            raise TypeError,"Type error setting beeper state of SMU. Examples of correct state are ('ON','OFF',True,0)"       

    def setOutputState(self,state):
        """ Turns the SMU on or off depending on state. state can be ('ON'/True/1), ('OFF',False,0)"""
        if state=="ON" or state==1 or state==True:
            self._smu.write(":OUTP ON")
        elif state=="OFF" or state==0 or state==False:
            self._smu.write(":OUTP OFF")
        else:
            raise TypeError,"Type error setting state of SMU. Examples of correct state are ('ON','OFF',True,0)"
        # wait for the output to finish switching.
        sleep(10e-3)
        # set the state so we can keep track of it
        self.state=state



class VisaConnection(visaconnection.VisaConnection):
    """ Abstraction of the VISA connection for consistency between implementation of instrument classes """
    def __init__(self,addr,defaultCurrent,t=5):
        super(VisaConnection,self).__init__(addr,t)  
        self.defaultCurrent=defaultCurrent
    def __del__(self):
        self.write(":OUTP OFF")
        self.write(":SOUR:CURR:RANGE 100e-3;:SOUR:CURR:LEV "+str(self.defaultCurrent))
        self.write("DISP:ENAB 1")
        self.write(":SYST:LOC")        






