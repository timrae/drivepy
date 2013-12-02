from __future__ import division
from drivepy.visaconnection import VisaConnection
from PyQt4.QtCore import *

class TemperatureController(QObject):
    """Class to communicate with the Scientific Instruments SI 9650 temperature controller / sensor via GPIB"""
    def __init__(self,addr="GPIB::15",parent=None):
        super(TemperatureController, self).__init__(parent)
        self.tempController=VisaConnection(addr)
    @pyqtSlot()
    def getTemperature(self):
        #return float(self.tempController.read("T")[1:])
        try:
            temperature=float(self.tempController.read("T")[1:])
            self.emit(SIGNAL("tempDataReady"),temperature)
            return temperature
        except Exception as e:
            pass
    @pyqtSlot()
    def getSetTemperature(self):
        #return float(self.tempController.read("S")[1:])
        self.emit(SIGNAL("setTempDataReady"),float(self.tempController.read("S")[1:]))
    def setTemperature(self,temperature):
        self.tempController.write("S"+"{:3.1f}".format(temperature))

