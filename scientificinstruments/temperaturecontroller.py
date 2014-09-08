from __future__ import division
from drivepy.visaconnection import VisaConnection
from PyQt4.QtCore import *
REMEASURE_ATTEMPTS=5

class TemperatureController(QObject):
    """Class to communicate with the Scientific Instruments SI 9650 temperature controller / sensor via GPIB"""
    def __init__(self,addr="GPIB::15",parent=None):
        super(TemperatureController, self).__init__(parent)
        self.tempController=VisaConnection(addr)
    @pyqtSlot()
    def getTemperature(self):
        #return float(self.tempController.read("T")[1:])
        attempt=1
        try:            
            response=self._readSafe("T")
        except Exception as e:
            pass
        temperature=float(response[1:])
        self.emit(SIGNAL("tempDataReady"),temperature)
        return temperature

    @pyqtSlot()
    def getSetTemperature(self):
        #return float(self.tempController.read("S")[1:])
        response=self._readSafe("S")
        self.emit(SIGNAL("setTempDataReady"),float(response[1:]))

    def setTemperature(self,temperature):
        self.tempController.write("S"+"{:3.1f}".format(temperature))

    def _readSafe(self,cmd):
        """ read command cmd a number of times until the expected response is returned """
        attempt=1        
        while attempt < REMEASURE_ATTEMPTS:
            response=self.tempController.readQuery(cmd)
            if response[0]==cmd:
                break
            else:
                attempt+=1
        if attempt < REMEASURE_ATTEMPTS:
            return response
        else:
            raise ReadError, "Error reading cmd " + cmd + " from temperature controller"

class ReadError(Exception): pass


