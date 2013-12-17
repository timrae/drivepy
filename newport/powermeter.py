from __future__ import division
import ctypes,time,string,numpy
READ_BUFFER_SIZE=64
DLL_NAME=os.path.join(os.path.dirname(__file__),"usbdll.dll")
SEP_STRING="\r\n"
END_OF_DATA_STR = "End of Data\r\n"
END_OF_HEADER_STR = "End of Header\r\n"
MAX_RANGE=4
READ_TIMEOUT=10

class PowerMeter(object):
    """ Creates a power meter object, from which we can take power meter readings using readPower() 
    or send commands/queries using sendCommand(command)."""
    def __init__(self,pid=0xcec7,*setupArgs):
        """ initializes the power meter object. pid is the product id for the power meter from the file
        NewportPwrMtr.inf e.g. in C:\Program Files\Newport\Newport USB Driver\Bin"""
        self.pid=pid
        self.connection=USBConnection(pid)
        self.setupMeter(*setupArgs)
    def reset(self):
        """ resets the connection in case it has frozen """
        del self.connection
        self.connection=USBConnection(self.pid)

    def buildRangeDic(self):
        """ Builds a dictionary giving the maximum power values for all range """
        self.rangeDic={}
        for r in range(MAX_RANGE):
            self.setRange(r)
            self.rangeDic[r]=self.getMaxPower()

    def setupMeter(self,wavelength=1300,autoRange=0,range=1,filterType=1,analogFilter=4,digitalFilter=10000,units=2):
        """ routine to setup the power meter to a predetermined state"""
        self.setWavelength(wavelength)
        self.setUnits(units)
        self.buildRangeDic()
        self.setRange(range)
        self.setAutoRange(autoRange)
        self.setAnalogFilter(analogFilter)
        self.setDigitalFilter(digitalFilter)
        self.setFilterType(filterType)
        self.initBuffer()

    def readPower(self):
        """ routine to read a single power measurement and return as float. 
        This is much faster than readPowerAuto() but requires range to be set correctly, and doesn't do any averaging."""
        c=self.connection
        return c.readFloat("PM:P?")

    def readPowerWithStatus(self):
        """ routine to read a single power measurement and return as float. 
        This is much faster than readPowerAuto() but requires range to be set correctly, and doesn't do any averaging."""
        self.connection.write("PM:PWS?")
        result=self.connection.read().strip().split(", ")
        power=float(result[0])
        statusCode=int(result[1],16)
        mask=[1920, 112, 8, 4, 2, 0]
        shift=[7,4,3,2,1,0]
        status=[(statusCode&mask[i]) >> shift[i] for i in range(len(mask))]
        statusDict={"units":status[0],"range":status[1],"detectorPresent":status[2],"ranging":status[3],"saturated":status[4],"overange":status[5]}
        return (power,statusDict)
        
    def readPowerN(self,n):
        """ Read fixed buffer of n samples """
        if n==1:
            return numpy.array(self.readPower())
        else:
            # Clear buffer, set size of buffer, then set enable true which will fill the buffer
            self.connection.write("pm:ds:clear")
            self.connection.write("pm:ds:size "+str(int(n)))
            self.connection.write("pm:ds:enable 1")
            # Wait for the samples to fill up
            timeout=False
            t0=time.time()
            while not timeout:
                numValues=int(self.connection.readFloat("PM:DS:Count?"))
                delay=time.time()-t0
                timeout=delay > READ_TIMEOUT
                if numValues >= n:
                    break
                elif self.readPower()>self.rangeDic[self.range]:
                    # sometimes "PM:DS:Count?" doesn't work when saturating, but a normal read does
                    raise SaturatingError
            if timeout: raise CommError, "Expected "+str(n)+" samples from power meter, but only received "+str(numValues)
            # Write the get command
            self.connection.write("pm:ds:get? +"+str(int(n)))
            # Prepare some variables
            responseBuffer=""
            lastReadStr=""
            endOfData=False
            # Read READ_BUFFER_SIZE bytes from the device until END_OF_DATA_STR is found or a read error occurs
            while not endOfData:
                readStr=self.connection.read()
                # Append the current read string
                responseBuffer=responseBuffer+readStr
                # See if END_OF_DATA_STR was found allowing for possibility that some of it is in last reading
                endOfData=string.find(lastReadStr+readStr,END_OF_DATA_STR)>=0
                lastReadStr=readStr
            # Find the indices where the data starts and ends
            dataStartIndex=string.find(responseBuffer,END_OF_HEADER_STR)+len(END_OF_HEADER_STR)
            dataEndIndex=string.find(responseBuffer,END_OF_DATA_STR)
            assert dataStartIndex!= -1 and dataEndIndex!=-1, "End of Header or End of Data message not found when reading from power meter"
            # Convert from newline separated string sequence to numpy array of floats and return
            dataSplit=responseBuffer[dataStartIndex:dataEndIndex].splitlines()
            return numpy.array([float(val) for val in dataSplit])

    def readPowerAuto(self,tau=200,timeout=10):
        """ Reads the power using custom auto-range functionality and averaged over specified time interval tau in ms.
        A timeout can be specified in seconds for the auto-range and re-measure, where we give up on trying to find a more accurate reading. 
        If the timeout is invoked, it means the power is fluctuating too much with time, and so tau should be increased."""
        self.t0=time.time()
        # Automatically remeasure if there was a comm. error until timeout occurs
        while 1:
            try:
                power=self._readPowerAuto(tau,timeout)
                break
            except CommError as e:
                if time.time()-self.t0 < timeout:
                    pass
                else:
                    # If timeout occurs, re-raise the (same) error
                    raise
        del self.t0
        return power

    def _readPowerAuto(self,tau,timeout):
        """ Hidden recursive method which does the main work for readPowerAuto() """
        n=int(numpy.ceil(tau))
        # Read an array of samples length tau ms
        try:
            powerSamples=self.readPowerN(n)
        except SaturatingError:
            powerSamples=numpy.inf
        except CommError as e:
            # If the length of array is wrong then clear the command queue and try again, if still wrong then let exception propagate
            queueStr=self.connection.clearComQueue()
            try:
                powerSamples=self.readPowerN(n)
            except CommError as e:
                raise
        # Calculate the maximum from the samples
        maxPower=numpy.max(powerSamples)
        # Increase the range if power larger than 99% the measurement limit and return remeasurement
        if maxPower > 0.99*self.rangeDic[self.range]:
            if self.range < MAX_RANGE:
                self.setRange(self.range+1)
                time.sleep(1)
                return self._readPowerAuto(tau,timeout)
            elif maxPower <= self.rangeDic[self.range]:
                # If max range and between 99%-100% of maximum power then return average
                return numpy.mean(powerSamples)
            else:
                raise CommError, "The measured power was too large. Please enable the attenutator and restart the program"
        # Reduce the range if power smaller than 99% of the measurement limit of the next lowest range and no timeout has occured
        elif self.range > 0 and maxPower < 0.99*self.rangeDic[self.range-1] and (time.time()-self.t0)<timeout:
            self.setRange(self.range-1)
            time.sleep(1)
            return self._readPowerAuto(tau,timeout)
        # Otherwise return the mean of the n samples
        else:
            return numpy.mean(powerSamples)
        
    def setRange(self,range):
        """ Set the range of the ADC given integer between 0 and MAX_RANGE """
        self.range=range
        self.connection.write("PM:RAN "+str(range))
    
    def getRange(self):
        return self.connection.readFloat("PM:RAN?")

    def setAutoRange(self,autoRange):
        self.connection.write("PM:Auto "+str(int(autoRange)))

    def getMaxPower(self):
        """ returns the maximum readable power for the current float """
        return self.connection.readFloat("PM:MAX:Power?")

    def setWavelength(self,wavelength):
        self.connection.write("PM:Lambda "+str(wavelength))

    def setUnits(self,units):
        self.connection.write("PM:UNITS "+str(units))

    def setFilterType(self,filterType):
        """ Sets the filter type: 0->none, 1->analog, 2->digital, 3-> analog+digital """
        self.connection.write("PM:FILT "+str(filterType))

    def setAnalogFilter(self,analogFilter):
        """ Sets the frequency for analog filter: 0->None, 1->250kHz, 2-> 12.5kHz, 3-> 1kHz, 4-> 5Hz """
        self.connection.write("PM:ANALOGFILTER "+str(analogFilter))

    def setDigitalFilter(self,digitalFilter):
        """ Sets the number of samples for digital filter """
        self.connection.write("PM:DIGITALFILTER "+str(digitalFilter))

    def initBuffer(self,interval=10,circular=False):
        " Set buffer interval (ms) and type """
        # NOTE!interval=1 should lead to 1ms interval, but from trial and error it appears that interval=10 gives a 1ms interval!
        self.connection.write("pm:ds:interval "+str(interval))
        self.connection.write("pm:ds:buffer "+str(int(circular)))

    def readErrors(self):
        """ Return tuple with error code and descriptive string """
        self.connection.write("ERRSTR?")
        result=self.connection.read().split(",")
        return (int(result[0]),result[1].strip())

    def sendCommand(self,command):
        """ Send a string command to the power meter. If the command is a query (i.e. ends with a "?"
        then the method returns the response from the power meter, otherwise returns nothing"""
        assert type(command)==str, "sendCommand requires a string command"
        if command[-1]=="?":
            return self.connection.readFloat(command)
        else:
            self.connection.write(command)
        
class USBConnection(object):
    """ Abstraction of the low level connection to USB bus so that destructor can be used without circular
    references as per http://eli.thegreenplace.net/2009/06/12/safely-using-destructors-in-python/.
    This class is essentially a wrapper for the Newport USB Driver library usbdll.dll"""
    def __init__(self,pid):
        """ Open the USB connection and get the device ID for future communication """
        self.readBufferSize=READ_BUFFER_SIZE
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
        s=self.lib.newp_usb_send_ascii(self.id, writeString+SEP_STRING, len(writeString+SEP_STRING))
        if s<0:
            raise CommError, "Writing of command '" + writeString + "' was not succesful and returned " + str(s)
    
    def read(self):
        """ Reads the response from power meter """
        readBuffer=ctypes.create_string_buffer(self.readBufferSize)
        numBytesRead=ctypes.c_int(0)
        s=self.lib.newp_usb_get_ascii(self.id,readBuffer,self.readBufferSize,ctypes.byref(numBytesRead))
        if s<0:
            raise CommError, "Reading from power meter was not succesful and returned " + str(s)
        return readBuffer.value

       
    def readFloat(self,queryString):
        """ Writes the query command in queryString, then reads the response and returns it """
        self.write(queryString)
        returnString=self.read()
        # Also need to do error checking on the status, but for now just raise exception if too large
        return float(returnString.strip())

    def clearComQueue(self):
        """ Clears the communication queue in case communication was interrupted somehow. Probably not needed. """
        commStr=""
        while 1:
            try:
                commStr+=self.read()
            except CommError:
                break
        return commStr

class CommError(Exception): pass
class SaturatingError(Exception): pass
class PowerMeterLibraryError(Exception): pass
