from __future__ import division
from numpy import *
from drivepy import visaconnection

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

    def setAttenuator(self, autoMode = false, attn = 10):
        """ Set autoMode (true/false) and attn value in steps of 10dB"""
        if autoMode:
            self._sa.write("AAT 1")
        else:
            self._sa.write("AAT 0")
            self._sa.write("AT "+str(attn))

    def setSweepTime(self, autoMode = false, time = 20):
        """ Set autoMode (true/false) and sweep time in ms"""
        if autoMode:
            self._sa.write("AST 1")
        else:
            self._sa.write("AST 0")
            self._sa.write("ST "+str(time)+"MS")

    def obtainSpectrum(self):
        """ Obtain a spectrum from the OSA. Based on Example VB-5 in the user manual for the Q8384 """
        self._sa.write("TS")                        # Start a sweep
        self._sa.write("BIN 0")                     # Set format to ASCII
        y = zeros(self._numPoints)                  # Create empty array to hold data
        for idx in range(len(y)):
            self._sa.write("XMA? "+str(idx)+",1")   # Tell SA to send us point i
            y[idx] = float(self._sa.read())/100     # Read the value and put it into data array. Measured in steps of 0.01dB

        x = zeros(self._numPoints)  # TODO: What to set this to?
        return (x,y)

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




