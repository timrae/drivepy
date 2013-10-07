from __future__ import division
import ctypes
import time
DLL_NAME="usbdll.dll"

class PowerMeter(object):
    """ Creates a power meter object, from which we can take power meter readings using readPower() 
    or send commands/queries using sendCommand(command)."""
    def __init__(self,pid=0xcec7):
        """ initializes the power meter object. pid is the product id for the power meter from the file
        NewportPwrMtr.inf e.g. in C:\Program Files\Newport\Newport USB Driver\Bin"""
        self.pid=pid
        self.connection=USBConnection(pid)
        self.setupMeter()
    def reset(self):
        """ resets the connection in case it has frozen """
        del self.connection
        self.connection=USBConnection(self.pid)
    
    def setupMeter(self,wavelength=1300):
        """ routine to setup the power meter to a predetermined state"""
        self.connection.write("PM:Lambda "+str(wavelength)+";")
        self.connection.write("PM:UNITS 2; PM:AUTO 1; PM:FILT 3")
        self.connection.write("PM:ANALOGFILTER 3; PM:DIGITALFILTER 10")
        
    def readPower(self):
        """ routine to read a single power measurement """
        c=self.connection
        # Probably unnecessary, but written in manual
        c.write("PM:MODE 0; PM:DS:EN 0; PM:DS:CLEAR; PM:DS:INT 0.1; PM:DS:SIZE 1; PM:BUF 0; PM:DS:EN 1")
        #powerStr=c.read("PM:DS:GET? 1")
        powerStr=c.read("PM:P?") # PM:DS:GET? not working so using this instead
        # also important to check for errors, see manual for command to do this
        return float(powerStr)
    def sendCommand(self,command):
        """ Send a string command to the power meter. If the command is a query (i.e. ends with a "?"
        then the method returns the response from the power meter, otherwise returns nothing"""
        assert type(command)==str, "sendCommand requires a string command"
        if command[-1]=="?":
            return self.connection.read(command)
        else:
            self.connection.write(command)
        
class USBConnection(object):
    """ Abstraction of the low level connection to USB bus so that destructor can be used without circular
    references as per http://eli.thegreenplace.net/2009/06/12/safely-using-destructors-in-python/.
    This class is essentially a wrapper for the Newport USB Driver library usbdll.dll"""
    def __init__(self,pid):
        """ Open the USB connection and get the device ID for future communication """
        self.readBufferSize=64
        try:
            self.lib=ctypes.WinDLL(DLL_NAME)
        except Exception,e:
            raise PowerMeterLibraryError,"Could not load the power meter library " + DLL_NAME + ". \n" + e.args[0]
        # Open the usb device specified by pid
        s=self.lib.newp_usb_open_devices(pid,False,ctypes.byref(ctypes.c_int(0)))
        if s<0:
            raise CommError, "Connection to pid=" + str(pid) + " could not be initialized and returned " + str(s)
        # Retrieve the device ID assigned above
        readBuffer=ctypes.create_string_buffer(1024)
        s=self.lib.newp_usb_get_device_info(readBuffer)
        if s<0:
            raise CommError, "Connection to pid=" + str(pid) + " successful, but get_device_info failed and returned " + str(s)
        deviceInfoList=readBuffer.value.split(',')
        if len(deviceInfoList)>2:
            raise CommError, "More than one Newport instrument detected on the USB bus which is not supported"
        self.id=int(deviceInfoList[0])
    def __del__(self):
        """ Destructor method unitializes the USB connection """
        self.lib.newp_usb_uninit_system()
    def write(self,writeString):
        """ Writes a single command to the USB device"""
        s=self.lib.newp_usb_send_ascii(self.id, writeString+"\r\n", len(writeString+"\r\n"))
        if s<0:
            raise CommError, "Writing of command '" + writeString + "' was not succesful and returned " + str(s)
    def read(self,queryString):
        """ Writes the query command in queryString, then reads the response and returns it """
        self.write(queryString)
        readBuffer=ctypes.create_string_buffer(self.readBufferSize)
        numBytesRead=ctypes.c_int(0)
        s=self.lib.newp_usb_get_ascii(self.id,readBuffer,self.readBufferSize,ctypes.byref(numBytesRead))
        if s<0:
            raise CommError, "Reading of response from command '" + queryString + "' was not succesful and returned " + str(s)
        # Also need to do error checking on the status, but for now just raise exception if too large
        powerValue=float(readBuffer.value.strip())
        if powerValue>1000:
            raise CommError,"Power value was unreasonably large"
        return powerValue

class CommError(Exception): pass
class PowerMeterLibraryError(Exception): pass