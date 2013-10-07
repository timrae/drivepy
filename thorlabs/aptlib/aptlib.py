from __future__ import division
import aptconsts as c
import ftd2xx
import time
from struct import pack,unpack

# In debug mode we print out all messages which are sent (in hex)
DEBUG_MODE=False

class MessageReceiptError(Exception): pass

class AptDevice(object):
    """ Wrapper around the Apt protocol via the ftd2xx driver for USB communication with the FT232BM USB peripheral chip in the APT controllers.
   Below is a list of messages defined for all APT devices. Only a small portion of them necessary have been implemented so far taken from the spec
   http://www.thorlabs.com/software/apt/APT_Communications_Protocol_Rev_9.pdf
   The ftd2xx driver specification is also useful:
   http://www.ftdichip.com/Support/Documents/ProgramGuides/D2XX_Programmer's_Guide(FT_000071).pdf"""

    def __init__(self,hwser=None):
        if hwser==None:
            # If only one device connected in the system we can open without specifying anything
            try:
                self.device= device = ftd2xx.open()
            except ftd2xx.DeviceError:
                # If the device fails to open the first time, it's probably because it wasn't closed properly. Simply opening again seems to fix this
                self.device= device = ftd2xx.open()
        else:
            # Open by serial number. Not implemented yet
            pass
        # Inititalize the device according to FTD2xx and APT requirements
        device.setBaudRate(ftd2xx.defines.BAUD_115200)
        device.setDataCharacteristics(ftd2xx.defines.BITS_8,ftd2xx.defines.STOP_BITS_1,ftd2xx.defines.PARITY_NONE)
        self.delay()
        device.purge()
        self.delay()
        device.resetDevice()
        device.setFlowControl(ftd2xx.defines.FLOW_RTS_CTS)
        device.setTimeouts(c.WRITE_TIMEOUT,c.READ_TIMEOUT)
        self.writeMessage(c.MGMSG_HW_NO_FLASH_PROGRAMMING)  # not sure if this is necessary but Thor Labs do it so just copy them
        serNum,model,type,firmwareVer,notes,hwVer,modState,numCh=self.query(c.MGMSG_HW_REQ_INFO,c.MGMSG_HW_GET_INFO)[-1]
        print("Connected to %s device with serial number %d. Notes about device: %s"%(model.replace('\x00', ''),serNum,notes.replace('\x00', '')))
        
    def __del__(self):
        self.device.close()

    def writeMessage(self,messageID,param1=0,param2=0,destID=c.GENERIC_USB_ID,sourceID=c.HOST_CONTROLLER_ID,dataPacket=None):
        """ Send message to device given messageID, parameters 1 & 2, destination and sourceID ID, and optional data packet, 
        where dataPacket is an array of numeric values. The method converts all the values to hex according to the protocol
        specification for the message, and sends this to the device."""
        if dataPacket!=None:
            # If a data packet is included then header consists of concatenation of: messageID (2 bytes),number of bytes in dataPacket (2 bytes), destination byte with MSB=1 (i.e. or'd with 0x80), sourceID byte
            dataPacketStr=pack(c.getPacketStruct(messageID) , *dataPacket)
            message=pack(c.HEADER_FORMAT_WITH_DATA , messageID , len(dataPacketStr) , destID|0x80 , sourceID) + dataPacketStr
        else:
            # If no data packet then header consists of concatenation of: messageID (2 bytes),param 1 byte, param2 bytes,destination byte, sourceID byte
            message=pack(c.HEADER_FORMAT_WITHOUT_DATA,messageID,param1,param2,destID,sourceID)
        if DEBUG_MODE: self.disp(message,"TX:  ")
        numBytesWritten=self.device.write(message)
    
    def query(self,txMessageID,rxMessageID,param1=0,param2=0,destID=c.GENERIC_USB_ID,sourceID=c.HOST_CONTROLLER_ID,dataPacket=None):
        """ Sends the REQ query message given by txMessageID, and then retrieves the GET response message given by rxMessageID from the device.
        param1,param2,destID,and sourceID for the REQ message can also be specified if non-default values are required.
        The return value is a 7 element tuple with the first 6 values the messageID,param1,param2,destID,sourceID from the GET message header
        and the final value of the tuple is another tuple containing the values of the data packet, or None if there was no data packet """
        
        self.writeMessage(txMessageID,param1,param2,destID,sourceID,dataPacket)
        response=self.readMessage()
        if response[0]!=rxMessageID:
            raise MessageReceiptError, "Error querying apt device when sending messageID " + hex(txMessageID) + ".... Expected to receive messageID " + hex(rxMessageID) + " but got " + hex(response[0])
        return response             

    def readMessage(self):
        """ Read a single message from the device and return tuple of messageID, parameters 1 & 2, destination and sourceID ID, and data packet 
        (if included), where dataPacket is a tuple of all the message dependent parameters decoded from hex, 
        as specified in the protocol documentation. Normally the user doesn't need to call this method as it's automatically called by query()"""
        # Read 6 byte header from device
        headerRaw=self.device.read(c.NUM_HEADER_BYTES)
        if headerRaw=="": raise MessageReceiptError, "Timeout reading from the device"
        # Check if a data packet is attached (i.e. get the 5th byte and check if the MSB is set)
        isDataPacket=unpack("B",headerRaw[4])[0]>>7
        # Read data packet if it exists, and interpret the message accordingly
        if isDataPacket:
            header=unpack(c.HEADER_FORMAT_WITH_DATA,headerRaw)
            messageID=header[0]
            dataPacketLength=header[1]
            param1=None
            param2=None
            destID=header[2]
            sourceID=header[3]
            destID=destID&0x7F
            dataPacketRaw=self.device.read(dataPacketLength)
            if DEBUG_MODE: self.disp(headerRaw+dataPacketRaw,"RX:  ")
            # If an error occurs at the following line, it's likely due to a problem with the data for packet structure in aptconsts
            dataPacket=unpack(c.getPacketStruct(messageID),dataPacketRaw)
        else:
            if DEBUG_MODE: self.disp(headerRaw,"RX:  ")
            header=unpack(c.HEADER_FORMAT_WITHOUT_DATA,headerRaw)
            messageID=header[0]
            param1=header[1]
            param2=header[2]
            destID=header[3]
            sourceID=header[4]
            dataPacket=None
        # Return tuple containing all the message parameters
        return (messageID,param1,param2,destID,sourceID,dataPacket)
    
    def delay(self,delayTime=c.PURGE_DELAY):
        """ Sleep for specified time given in ms """
        time.sleep(delayTime/1000)
        
    def disp(self,s,prefixStr="",suffixStr=""):
        """ Convenience method to give the hex for a raw string """
        dispStr=prefixStr + str([hex(ord(c)) for c in s]) + suffixStr
        print(dispStr)

class _AptPiezo(AptDevice):
    """ Wrapper around the messages of the APT protocol specified for piezo controller. The method names (and case) are set the same as in the Thor Labs ActiveX control for compatibility """   
    def __init__(self,hwser=None):
        super(_AptPiezo, self).__init__(hwser)
        self.maxVoltage=75.0                # for some unknown reason our device isn't responding to self.GetMaxOPVoltage()
        self.maxExtension=self.GetMaxTravel()
        for ch in [c.CHANNEL_1,c.CHANNEL_2]:
            self.EnableHWChannel(ch)
            self.writeMessage(c.MGMSG_MOD_SET_DIGOUTPUTS , 0, 0x59) # Thor Labs are doing this, but I have no idea if it's necessary, or what 0x59 is since this is supposed to be 0
            self.writeMessage(c.MGMSG_PZ_SET_NTMODE,0x01)
            self.SetControlMode(ch)
            self.SetVoltOutput(ch)
            self.writeMessage(c.MGMSG_PZ_SET_INPUTVOLTSSRC,dataPacket=(ch,c.PIEZO_INPUT_VOLTS_SRC_SW))
            self.writeMessage(c.MGMSG_PZ_SET_PICONSTS,dataPacket=(ch,c.PIEZO_PID_PROP_CONST,c.PIEZO_PID_INT_CONST))
            self.writeMessage(c.MGMSG_PZ_SET_IOSETTINGS,dataPacket=(ch,c.PIEZO_AMP_CURRENT_LIM,c.PIEZO_AMP_LP_FILTER,c.PIEZO_AMP_FEEDBACK_SIGNAL,c.PIEZO_AMP_BNCMODE_LVOUT))
            # If we wanna receive status update messages then we need to send MGMSG_HW_START_UPDATEMSGS
            # We would additionally need to send server alive messages every 1s, e.g. MGMSG_PZ_ACK_PZSTATUSUPDATE for Piezo
            # However if we don't need broadcasting of the position etc we can just fetch the status via GET_STATUTSUPDATES
        
    def EnableHWChannel(self,channelID=c.CHANNEL_1):
        """ Sent to enable the specified drive channel. """       
        self.writeMessage(c.MGMSG_MOD_SET_CHANENABLESTATE,channelID,c.CHAN_ENABLE_STATE_ENABLED)

    def DisableHWChannel(self,channelID=c.CHANNEL_1):
        """ Sent to disable the specified drive channel. """       
        self.writeMessage(c.MGMSG_MOD_SET_CHANENABLESTATE,channelID,c.CHAN_ENABLE_STATE_DISABLED)
    
    def SetControlMode(self,channelID=c.CHANNEL_1,controlMode=c.PIEZO_OPEN_LOOP_MODE):
        """ When in closed-loop mode, position is maintained by a feedback signal from the piezo actuator. 
        This is only possible when using actuators equipped with position sensing.
        This method sets the control loop status The Control Mode is specified in the Mode parameter as per the main documentation """
        self.writeMessage(c.MGMSG_PZ_SET_POSCONTROLMODE,channelID,controlMode)

    def GetControlMode(self,channelID=c.CHANNEL_1):
        """ Get the control mode of the APT Piezo device"""
        response=self.query(c.MGMSG_PZ_REQ_POSCONTROLMODE,c.MGMSG_PZ_GET_POSCONTROLMODE,channelID)
        assert response[1]==channelID, "inconsistent channel in response message from piezocontroller"
        return response[2]
        
    def SetVoltOutput(self,channelID=c.CHANNEL_1,voltOutput=0.0):
        """ Used to set the output voltage applied to the piezo actuator. 
        This command is applicable only in Open Loop mode. If called when in Closed Loop mode it is ignored."""
        voltParam=self._voltageAsFraction(voltOutput)
        self.writeMessage(c.MGMSG_PZ_SET_OUTPUTVOLTS,dataPacket=(channelID,voltParam))

    def GetVoltOutput(self,channelID=c.CHANNEL_1):
        """ Get the output voltage of the APT Piezo device. Only applicable when in open-loop mode """
        response=self.query(c.MGMSG_PZ_REQ_OUTPUTVOLTS,c.MGMSG_PZ_GET_OUTPUTVOLTS,channelID)
        dataPacket=response[-1]
        assert dataPacket[0]==channelID, "inconsistent channel in response message from piezocontroller"
        return self._fractionAsVoltage(dataPacket[1])
            
    def SetPosOutput(self,channelID=c.CHANNEL_1,posOutput=10.0):
        """ Used to set the output position of piezo actuator. This command is applicable only in Closed Loop mode. 
        If called when in Open Loop mode it is ignored. 
        The position of the actuator is relative to the datum set for the arrangement using the ZeroPosition method."""
        posParam=self._positionAsFraction(posOutput)
        self.writeMessage(c.MGMSG_PZ_SET_OUTPUTPOS,dataPacket=(channelID,posParam))

    def GetPosOutput(self,channelID=c.CHANNEL_1):
        """ Get the current position of the APT Piezo device. Only applicable when in closed-loop mode"""
        response=self.query(c.MGMSG_PZ_REQ_OUTPUTPOS,c.MGMSG_PZ_GET_OUTPUTPOS,channelID)
        dataPacket=response[-1]
        assert dataPacket[0]==channelID, "inconsistent channel in response message from piezocontroller"
        return self._fractionAsPosition(dataPacket[1])

    def ZeroPosition(self,channelID=c.CHANNEL_1):
        """ This function applies a voltage of zero volts to the actuator associated with the channel specified by the lChanID parameter, and then reads the position. 
        This reading is then taken to be the zero reference for all subsequent position readings. 
        This routine is typically called during the initialisation or re-initialisation of the piezo arrangement. """
        self.writeMessage(c.MGMSG_PZ_SET_ZERO,channelID)

    def GetMaxTravel(self,channelID=c.CHANNEL_1):
        """ In the case of actuators with built in position sensing, the Piezoelectric Control Unit can detect the range of travel of the actuator 
        since this information is programmed in the electronic circuit inside the actuator. 
        This function retrieves the maximum travel for the piezo actuator associated with the channel specified by the Chan Ident parameter, 
        and returns a value (in microns) in the Travel parameter."""
        response=self.query(c.MGMSG_PZ_REQ_MAXTRAVEL,c.MGMSG_PZ_GET_MAXTRAVEL,channelID)
        dataPacket=response[-1]
        assert dataPacket[0]==channelID, "inconsistent channel in response message from piezocontroller"
        return dataPacket[1]*c.PIEZO_TRAVEL_STEP

    def GetMaxOPVoltage(self,channelID=c.CHANNEL_1):
        """ The piezo actuator connected to the unit has a specific maximum operating voltage range: 75, 100 or 150 V. 
        This function gets the maximum voltage for the piezo actuator associated with the specified channel."""
        response=self.query(c.MGMSG_PZ_REQ_OUTPUTMAXVOLTS,c.MGMSG_PZ_GET_OUTPUTMAXVOLTS,channelID)
        dataPacket=response[-1]
        assert dataPacket[0]==channelID, "inconsistent channel in response message from piezocontroller"
        return dataPacket[1]*c.PIEZO_VOLTAGE_STEP

    def LLGetStatusBits(self,channelID=c.CHANNEL_1):
        """ Returns a number of status flags pertaining to the operation of the piezo controller channel specified in the Chan Ident parameter. 
        These flags are returned in a single 32 bit integer parameter and can provide additional useful status information for client application development. 
        The individual bits (flags) of the 32 bit integer value are described in the main documentaton."""
        response=self.query(c.MGMSG_PZ_REQ_PZSTATUSBITS,c.MGMSG_PZ_GET_PZSTATUSBITS,channelID)
        dataPacket=response[-1]
        assert dataPacket[0]==channelID, "inconsistent channel in response message from piezocontroller"
        return dataPacket[1]

    # Helper methods for the above main methods. Change to mixed case since no need for compatibility with ActiveX control
    def _voltageAsFraction(self,voltage):
        """ specify voltage as short representing fraction of max voltage"""
        return round(c.PIEZO_MAX_VOLT_REPR*voltage/self.maxVoltage) 

    def _fractionAsVoltage(self,voltFraction):
        """ convert voltage from short representing fraction of max voltage"""
        return voltFraction/c.PIEZO_MAX_VOLT_REPR*self.maxVoltage

    def _positionAsFraction(self,position):
        """ specify position as short representing fraction of max displacement. Apparently the max value depends on the unit though :( it might be 0xFFFF"""
        return round(c.PIEZO_MAX_POS_REPR*position/self.maxExtension) 

    def _fractionAsPosition(self,positionFraction):
        """ convert position from short representing fraction of max displacement"""
        return positionFraction/c.PIEZO_MAX_POS_REPR*self.maxExtension

class AptPiezo(_AptPiezo):
    """ This class contains higher level methods not provided in the Thor Labs ActiveX control, but are very useful nonetheless """
    def getEnableState(self,channel):
        response=self.query(c.MGMSG_MOD_REQ_CHANENABLESTATE,c.MGMSG_MOD_GET_CHANENABLESTATE,channel)
        assert response[1]==channel
        assert response[2]==c.CHAN_ENABLE_STATE_ENABLED or response[2]==c.CHAN_ENABLE_STATE_DISABLED, "Unrecognized enable state received"
        return response[2]==c.CHAN_ENABLE_STATE_ENABLED
    
    def isZeroing(self,channel):
        """ Check to see if the piezo controller is in the middle of zeroing (6th bit True)"""
        StatusBits=self.LLGetStatusBits(channel)
        return (StatusBits>>5) & 1

    def setPosition(self,channel,position):
        """ Move to specified position if valid, and wait for the measured position to stabilize """
        if position>=0 and position <= self.maxExtension:
            self.SetPosOutput(channel,position)
            t0=time.time()
            while abs(position-self.GetPosOutput(channel))>1.01*c.PIEZO_POSITION_ACCURACY:
                if (time.time()-t0)>c.PIEZO_MOVE_TIMEOUT:
                    print("Timeout error moving to "+str(position)+ 'um on channel '+str(channel))
                    break 
                else:
                    time.sleep(10e-3)

    def getPosition(self,channel):
        """ Get the position of the piezo. This is simply a wrapper for GetPosOutput using mixedCase """
        return self.GetPosOutput(channel)

    def zero(self,channel):
        """ Call the zero method and wait for it to finish """       
        self.ZeroPosition(channel)
        t0=time.time()
        while self.isZeroing(channel):
            if (time.time()-t0)>c.PIEZO_ZERO_TIMEOUT:
                print("Timeout error zeroing channel "+str(channel))
                break 
            else:
                time.sleep(500e-3)

    def moveToCenter(self,channel):
        """ Moves the specified channel to half of its maximum extension"""
        self.setPos(channel,self.maxExtension/2)

    
if __name__== '__main__': 
    p=AptPiezo()
    for ch in [c.CHANNEL_1,c.CHANNEL_2]:
        p.SetControlMode(ch,c.PIEZO_CLOSED_LOOP_MODE)
        p.zero(ch)
        p.moveToCenter(ch)
    pass


