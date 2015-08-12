from __future__ import division
from numpy import *
from drivepy import visaconnection

# Mapping of index to resolution bandwidth in Hz
RBW_DICT={0:30, 1:100, 2:300, 3:1e3, 4:3e3, 5:10e3, 6:30e3, 7:100e3, 8:300e3, 9:1e6, 13:10, 14:3e6}
VBW_DICT={0:1, 1:10, 2:100, 3:1e3, 4:10e3, 5:100e3, 6:float("inf"), 7:1e6, 8:3, 9:30, 10:300, 11:3e3, 12:30e3, 13:300e3, 14:3e6}

class SpectrumAnalyzer(object):
    """ Class for the Anritsu spectrum analyzer which provides high level commands for reading spectrums"""
    def __init__(self,addr="GPIB::2",timeout=60):
        self._sa=VisaConnection(addr,timeout)
        self._sa.write("*RST")
        self._numPoints = 501;

    def setSpan(self,span):
        """ Sets the measurement span for SA in GHz"""
        self._sa.write("SP "+str(span)+"GHZ")

    def setCenter(self,center):
        """ Sets the center wavelength for the SA in GHz"""
        self._sa.write("CF "+str(center)+"GHz")
    
    def setNumPoints(self,numPoints):
        """ Sets the number of sampling points """
        self._numPoints = numPoints

    def setAttenuator(self, autoMode = False, attn = 10):
        """ Set autoMode (True/False) and attn value in steps of 10dB"""
        if autoMode:
            self._sa.write("AAT 1")
        else:
            self._sa.write("AAT 0")
            self._sa.write("AT "+str(attn))

    def setSweepTime(self, autoMode = False, time = 20):
        """ Set autoMode (true/false) and sweep time in ms"""
        if autoMode:
            self._sa.write("AST 1")
        else:
            self._sa.write("AST 0")
            self._sa.write("ST "+str(time)+"MS")

    def setRbw(self,index):
        """ Set resolution bandwidth of spectrum analyzer -- see RBW_DICT for mapping"""
        self._sa.write("RBW "+str(index))

    def setVbw(self,index):
        """ Set video bandwidth of spectrum analyzer -- see VBW_DICT for mapping"""
        self._sa.write("VBW "+str(index))

    def getRbw(self):
        """ Return resolution bandwidth of specan in Hz"""
        rbwIndex=int(self._sa.readQuery("RBW?")[4:])
        return RBW_DICT[rbwIndex]

    def getNoiseBandwidth(self):
        """ Return the noise bandwidth of specan """
        return self.getRbw()*1.2

    def obtainSpectrum(self):
        """ Obtain a spectrum from the OSA. Based on Example VB-5 in the user manual for the Q8384 """
        self._sa.write("TS")                        # Start a sweep
        self._sa.write("BIN 0")                     # Set format to ASCII
        y = zeros(self._numPoints)                  # Create empty array to hold data
        # Get each of the 501 data points
        y = array([self.dbmToWatts(float(m)/100) for m in self._sa.readQuery("XMA? 0,501").split(",")])
        x = linspace(self.getStartFreq(), self.getStopFreq(), self._numPoints)
        return (x,y)

    def dbmToWatts(self,dbm):
        return 10**(dbm/10)/1000

    def getStartFreq(self):
        return float(self._sa.readQuery("STF?")[4:])

    def getStopFreq(self):
        return float(self._sa.readQuery("SOF?")[4:])

class VisaConnection(visaconnection.VisaConnection):
    """ Abstraction of the VISA connection for consistency between implementation of instrument classes """
    def __init__(self,addr,t):
        super(VisaConnection,self).__init__(addr,t)    
    def getFloatArray(self,request):
        """ retrieve an array of floats as specified by request string ("OSD0"|"OSD1") """
        n=int(self.lib.ask("ODN?"))
        self.write(request) # tell OSA to send wavelength or intensity depending on request string
        data=self.lib.read_values()
        if len(data)!=n:
            raise CommError, "received different number of data points than expected from spectrum analyzer"
        return array(data)
class CommError(Exception): pass




