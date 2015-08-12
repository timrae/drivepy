from __future__ import division
import visa

class VisaConnection(object):
    """ Abstraction of the VISA connection for consistency between implementation of instrument classes """
    def __init__(self,addr):
        rm = visa.ResourceManager()
        self.lib=rm.open_resource(addr)
        # Check if the device exists; if not then VisaIOError will be thrown
        try:
            self.lib.write("") 
        except visa.VisaIOError,e:
            raise IOError,"Could not create visa connection at GPIB::"+addr+". \n "+e.args[0]
    def write(self,writeString):
        self.lib.write(writeString)
    def readQuery(self,queryString):
        return self.lib.query(queryString)
    def wait(self,t):
        self.lib.wait_for_srq(timeout=t)
        # I want to read the status byte properly at some point, but for now I don't need it
        #status=vpp43.read_stb(self.vi)
        #if int(status)<0:
        #    raise CommError, "wait_for_srq() returned " + str(status) + " when talking to spectrum analyzer"
    def getFloatArray(self,request):
        """ retrieve an array of floats as specified by request string ("OSD0"|"OSD1") """
        self.write(request)
        data=self.lib.read_values()