"""
Control Thor Labs APT Devices without relying on the Thor Labs ActiveX control.
All that is required is the FTDI D2XX driver, which can be obtained for most platforms from the FTDI website:
http://www.ftdichip.com/Drivers/D2XX.htm

However if possible, it's recommended to install the official Thor Labs software, since this will 
automatically install the d2xx driver, and the APT User software is useful for checking everything works.
http://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=APT
"""
import sys
from aptlib import *

