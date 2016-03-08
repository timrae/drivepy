import time

class BasePowerMeter(object):
    def __init__(self, *args, **kwargs):
        self.timeout = None
        self.t0 = None
    def readPower(self, *args, **kwargs):
        """ routine to read a single power measurement """
        raise NotImplementedError("Subclass must implement abstract method")

    def readPowerAuto(self, timeout=10, *args, **kwargs):
        """ read power including automatic error handling for CommError """
        self.timeout = timeout
        self.t0=time.time()
        # Automatically remeasure if there was a comm. error until timeout occurs
        while 1:
            try:
                power=self.readPower(*args, **kwargs)
                break
            except CommError as e:
                if time.time()-self.t0 < timeout:
                    pass
                else:
                    # If timeout occurs, re-raise the (same) error
                    raise
        del self.t0
        return power
        
class CommError(Exception): pass
class PowerMeterLibraryError(Exception): pass