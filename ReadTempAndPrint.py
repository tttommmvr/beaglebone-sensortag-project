#!/usr/bin/env python
# Michael Saunby. April 2013
#
# Read temperature from the TMP006 sensor in the TI SensorTag
# It's a BLE (Bluetooth low energy) device so using gatttool to
# read and write values.
#
# Usage.
# sensortag_test.py BLUETOOTH_ADR
#
# To find the address of your SensorTag run 'sudo hcitool lescan'
# You'll need to press the side button to enable discovery.
#
# Notes.
# pexpect uses regular expression so characters that have special meaning
# in regular expressions, e.g. [ and ] must be escaped with a backslash.
#

import pexpect
import sys
import time

import pprint
import uuid

try:
    import ibmiotf.application
    import ibmiotf.device
except ImportError:
    # This part is only required to run the sample from within the samples
    # directory when the module itself is not installed.
    #
    # If you have the module installed, just use "import ibmiotf.application" & "import ibmiotf.device"
    import os
    import inspect
    cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],"../../src")))
    if cmd_subfolder not in sys.path:
        sys.path.insert(0, cmd_subfolder)
    import ibmiotf.application
    import ibmiotf.device


organization = "quickstart"
deviceType = "helloWorldDevice"
deviceId ="sensortg"  # str(uuid.uuid4())
print(deviceId)
appId = deviceId + "_receiver"
authMethod = None
authToken = None

def myAppEventCallback(event):
    print("Received live data from %s (%s) sent at %s: hello=%s x=%s" % (event.deviceId, event.deviceType, event.timestamp.strftime("%H:%M:%S"), data['hello'], data['x']))


#*****Connection*****#
# Initialize the application client.
try:
    appOptions = {"org": organization, "id": appId, "auth-method": authMethod, "auth-token": authToken}
    appCli = ibmiotf.application.Client(appOptions)
except Exception as e:
    print(str(e))
    sys.exit()

# Connect and configuration the application
# - subscribe to live data from the device we created, specifically to "greeting" events
# - use the myAppEventCallback method to process events
appCli.connect()
appCli.subscribeToDeviceEvents(deviceType, deviceId, "greeting")
appCli.deviceEventCallback = myAppEventCallback

# Initialize the device client.
try:
    deviceOptions = {"org": organization, "type": deviceType, "id": deviceId, "auth-method": authMethod, "auth-token": authToken}
    deviceCli = ibmiotf.device.Client(deviceOptions)
except Exception as e:
    print("Caught exception connecting device: %s" % str(e))
    sys.exit()
#*****Connection*****#

def floatfromhex(h):
    t = float.fromhex(h)
    if t > float.fromhex('7FFF'):
        t = -(float.fromhex('FFFF') - t)
        pass
    return t

# This algorithm borrowed from
# http://processors.wiki.ti.com/index.php/SensorTag_User_Guide#Gatt_Server
# which most likely took it from the datasheet. I've not checked it, other
# than noted that the temperature values I got seemed reasonable.
#
def calcTmpTarget(objT, ambT):
    m_tmpAmb = ambT/128.0
    Vobj2 = objT * 0.00000015625
    Tdie2 = m_tmpAmb + 273.15
    S0 = 6.4E-14            # Calibration factor
    a1 = 1.75E-3
    a2 = -1.678E-5
    b0 = -2.94E-5
    b1 = -5.7E-7
    b2 = 4.63E-9
    c2 = 13.4
    Tref = 298.15
    S = S0*(1+a1*(Tdie2 - Tref)+a2*pow((Tdie2 - Tref),2))
    Vos = b0 + b1*(Tdie2 - Tref) + b2*pow((Tdie2 - Tref),2)
    fObj = (Vobj2 - Vos) + c2*pow((Vobj2 - Vos),2)
    tObj = pow(pow(Tdie2,4) + (fObj/S),.25)
    tObj = (tObj - 273.15)
    print "%.2f C" % tObj
#   tempampt= ambT>> 2
#   tempobjt = objT>> 2
#   srtTempA ="temp obj= "+ tempampt/32
#   print(strTempA)

bluetooth_adr = sys.argv[1]
#print(bluetooth_adr)
tool = pexpect.spawn('gatttool -b ' + bluetooth_adr + ' -I')
#print(tool)
tool.expect('\[LE\]>')
print "Preparing to connect. You might need to press the side button..."
tool.sendline('connect')
# test for success of connect
tool.expect('Connection successful') #tool.expect('\[CON\].*>')
tool.sendline('char-write-cmd 0x27 01')
tool.expect('\[LE\]>')
print("asking temp")

def myOnPublishCallback():
        print("Confirmed event received by IoTF\n" )

deviceCli.connect()

while True:
    time.sleep(1)
    tool.sendline('char-read-hnd 0x24')
    tool.expect('descriptor: .*')
    rval = tool.after.split()
  ##  print(rval[4]+rval[3])

   # objT = floatfromhex(rval[2] + rval[1])
    ambT = rval[4] + rval[3]

    ambT ="0x"+ ambT
    ambT = ((int(ambT,16) >> 2) / 32)
    data = {'temp' : ambT}
   # print(data)
    print("ambiance temp= " + str(ambT))


    success = deviceCli.publishEvent("greeting", "json", data, qos=0, on_publish=myOnPublishCallback)
    if not success:
        print("Not connected to IoTF")
    time.sleep(1)

#to disconnect
deviceCli.disconnect()
appCli.disconnect()