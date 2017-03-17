#Filehandler config file (shared with main config)
CONFIG_FILE = "hueAndMe.cfg"
DOMOTICZ_REALM="Domoticz Home Automation"
MAX_DEVICES=27  # JMM 12/11/2015: 27 seems to be the magic limit for the Echo
EXCLUSION_DELIMITER='"'

import hashlib
import ConfigParser
import re
import urllib2
import json
import time

local_devices = {}
DOMOTICZ_USER = ""
DOMOTICZ_PASS = ""

def generate_unique_id(value):
	value = value.upper()
	value = value.replace(" ","")
	value = hashlib.md5(value).hexdigest()
	return ((":".join(a+b for a,b in zip(value[::2], value[1::2])))[:23])+"-0b"

def on(device):
	type = local_devices[device]['control']
	command = local_devices[device]['on']
	if (local_devices[device]['dimlevel']==0):
		get_url(command)
	local_devices[device]['dimlevel']=100

def off(device):
	type = local_devices[device]['control']
	command = local_devices[device]['off']
	get_url(command)
	local_devices[device]['dimlevel']=0
	
def dim(device,level):
	level = int(float(level)/254.0*100.0)
	type = local_devices[device]['control']
	command = local_devices[device]['dim']
	command = command.replace("{dim}",str(level))
	get_url(command)
	local_devices[device]['dimlevel']=level
	
def get_url(url):
	#print "FETCHING URL: "+ url
	global CONFIG_FILE, DOMOTICZ_REALM, DOMOTICZ_USER, DOMOTICZ_PASS
	authhandler = urllib2.HTTPDigestAuthHandler()
	authhandler.add_password(DOMOTICZ_REALM, url, DOMOTICZ_USER, DOMOTICZ_PASS)
	opener = urllib2.build_opener(authhandler)
	urllib2.install_opener(opener)
	response = urllib2.urlopen(url)
	trash = response.read()


def load_devices(devices, hue_devices):
	global CONFIG_FILE, DOMOTICZ_REALM, MAX_DEVICES, EXCLUSION_DELIMITER, local_devices, DOMOTICZ_USER, DOMOTICZ_PASS
	my_name = re.sub(r'.*?\.', r'', __name__)
	domoticzconfig = ConfigParser.SafeConfigParser()
	domoticzconfig.read(CONFIG_FILE)
	device_count = len(devices)-1
	internal_count = 0
	# Read config items
	DOMOTICZ_BASE_URL = domoticzconfig.get('domoticz','base_url')
	DOMOTICZ_USER = domoticzconfig.get('domoticz','username')
	DOMOTICZ_PASS = domoticzconfig.get('domoticz','password')
	if 'inclusions' in domoticzconfig.options('domoticz'):
		INCLUSIONS = domoticzconfig.get('domoticz','inclusions')
	else:
		INCLUSIONS = None
	if 'exclusions' in domoticzconfig.options('domoticz'):
		EXCLUSIONS = domoticzconfig.get('domoticz','exclusions')
	else:
		EXCLUSIONS = None

	if 'inclusion_keywords' in domoticzconfig.options('domoticz'):
		INCLUSION_KEYWORDS = domoticzconfig.get('domoticz','inclusion_keywords').split(",")
	else:
		INCLUSION_KEYWORDS = None
	if 'exclusion_keywords' in domoticzconfig.options('domoticz'):
		EXCLUSION_KEYWORDS = domoticzconfig.get('domoticz','exclusion_keywords').split(",")
	else:
		EXCLUSION_KEYWORDS = None


	DOMOTICZ_DEVICES_URL = DOMOTICZ_BASE_URL+"/json.htm?type=devices&used=true&order=Name"

	# Read Domoticz device list 
	#authhandler = urllib2.HTTPDigestAuthHandler()
	#authhandler.add_password(DOMOTICZ_REALM, DOMOTICZ_DEVICES_URL, DOMOTICZ_USER, DOMOTICZ_PASS)
	#opener = urllib2.build_opener(authhandler)
	#urllib2.install_opener(opener)
	response = urllib2.urlopen(DOMOTICZ_DEVICES_URL)
	domoticz_devices = response.read()
	domoticz_devices = json.loads(domoticz_devices)
	
	# Parse Domoticz device list into devices and hue devices
	for device in domoticz_devices['result']:
		quoted_device_name = "%s%s%s" % (EXCLUSION_DELIMITER, device['Name'], EXCLUSION_DELIMITER)
		if internal_count < MAX_DEVICES:
			if (
				(EXCLUSIONS and quoted_device_name in EXCLUSIONS) or
				(EXCLUSION_KEYWORDS and any(x in device['Name'] for x in EXCLUSION_KEYWORDS))
			):
				continue
			if (
				(INCLUSIONS and quoted_device_name not in INCLUSIONS) and 
				(INCLUSION_KEYWORDS and not any(x in device['Name'] for x in INCLUSION_KEYWORDS))
			):
				continue
			print "Adding %s..." % device['Name']
			device_count += 1
			internal_count += 1
			if (device['SubType'] == "SetPoint"):
				devices[str(device_count)] = {'control':'url','on':DOMOTICZ_BASE_URL+"/json.htm?type=devices&rid="+device['idx'],
									'off':DOMOTICZ_BASE_URL+"/json.htm?type=devices&rid="+device['idx'],
									'dim':DOMOTICZ_BASE_URL+"/json.htm?type=command&param=udevice&idx="+device['idx']+"&nvalue=0&svalue={dim}",
									'id':generate_unique_id(device['Name'].encode('ascii', 'ignore')),
									'name':device['Name'].encode('ascii', 'ignore'),
									'number':device_count,
									'dimlevel':0,
									'defined':my_name}
			else:
				devices[str(device_count)] = {'control':'url','on':DOMOTICZ_BASE_URL+"/json.htm?type=command&param=switchlight&idx="+device['idx']+"&switchcmd=On",
									'off':DOMOTICZ_BASE_URL+"/json.htm?type=command&param=switchlight&idx="+device['idx']+"&switchcmd=Off",
									'dim':DOMOTICZ_BASE_URL+"/json.htm?type=command&param=switchlight&idx="+device['idx']+"&switchcmd=Set%20Level&level={dim}",
									'id':generate_unique_id(device['Name'].encode('ascii', 'ignore')),
									'name':device['Name'].encode('ascii', 'ignore'),
									'number':device_count,
									'dimlevel':0,
									'defined':my_name}

			hue_devices[str(device_count)] = {"state":{"on": False, "bri": 255, "hue": 14924, "sat": 143,"effect":"none",
								"xy":[0.4589,0.4103],"ct":365,"alert":"none","colormode":"hs",
								"reachable":True}, "type":"Extended color light","name":device['Name'].encode('ascii', 'ignore'),"modelid":"LCT001",
								"manufacturername":"Philips","uniqueid":generate_unique_id(device['Name'].encode('ascii', 'ignore')),
								"swversion": "66010820", "pointsymbol": { "1":"none", "2":"none", 
								"3":"none", "4":"none", "5":"none", "6":"none", "7":"none", "8":"none" }}
		else:
			break
								
	local_devices = devices
	print "Loaded "+str(len(local_devices))+" devices from Domoticz."
	
	
