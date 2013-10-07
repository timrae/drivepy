from __future__ import division
from numpy import *
import visaconnection

class SpectrumAnalyzer(object):
    """ Class for the Advantest optical spectrum analyzer which provides high level commands for reading spectrums"""
    def __init__(self,addr="GPIB::10",timeout=60):
        self._osa=VisaConnection(addr,timeout)
        self._osa.write("*RST")
    def setSpan(self,span):
        """ Sets the measurement span for OSA in nm"""
        self._osa.write("SPA "+str(span)+"NM")
    def setCenter(self,center):
        """ Sets the center wavelength for the OSA in nm"""
        self._osa.write("CEN "+str(center)+"NM")
    def setNumPoints(self,numPoints):
        """ Sets the number of sampling points """
        self._osa.write("SPT "+str(numPoints))
    def setResolution(self,res):
        """ Sets measurement resolution """
        self._osa.write("RES "+str(res))
    def setSweepMode(self,sweepIndex=2):
        """ Sets the sweep mode given the index """
        self._osa.write("SWE "+str(sweepIndex))

    def obtainSpectrum(self):
        """ Obtain a spectrum from the OSA. Based on Example VB-5 in the user manual for the Q8384 """
        self._osa.write("MSK254") # Set mask byte
        self._osa.write("SRQ1")   # Tell OSA to send SRQ interrupt when it finishes measuring
        self._osa.write("MEA1")   # Take a single spectrum measurement
        self._osa.wait(20*60) # Wait for the SRQ interrupt before proceeding (20min timeout)
        self._osa.write("FMT0,HED0,SDL2") # set format:ASCII, header:OFF, delimiter: carriage return
        levelData=self._osa.getFloatArray("OSD0") # get the level data
        wavelengthData=self._osa.getFloatArray("OSD1") # get the wavelength data
        return (array(wavelengthData),array(levelData))  # return lambda,I as numpy arrays

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




