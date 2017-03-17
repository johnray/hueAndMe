#Filehandler config file (shared with main config)
CONFIG_FILE = "hueAndMe.cfg"
DISABLE_CHARACTER = "#"

import hashlib
import ConfigParser
import re
import urllib2

local_devices = {}

def generate_unique_id(value):
	value = value.upper()
	value = value.replace(" ","")
	value = hashlib.md5(value).hexdigest()
	return ((":".join(a+b for a,b in zip(value[::2], value[1::2])))[:23])+"-0b"

def on(device):
	type = local_devices[device]['control']
	command = local_devices[device]['on']
	get_url(command)

def off(device):
	type = local_devices[device]['control']
	command = local_devices[device]['off']
	get_url(command)
	
def dim(device,level):
	type = local_devices[device]['control']
	command = local_devices[device]['dim']
	command = command.replace("{dim}",str(level))
	get_url(command)
	
def get_url(url):
	#print "FETCHING URL: "+ url
	response = urllib2.urlopen(url)
	trash = response.read()

def load_devices(devices, hue_devices):
	global CONFIG_FILE, DISABLE_CHARACTER, local_devices
	my_name = re.sub(r'.*?\.', r'', __name__)
	config = ConfigParser.SafeConfigParser()
	config.read(CONFIG_FILE)
	sections = config.sections()
	device_count = len(devices)-1
	
	for section in sections:
		if section.lower() != "general" and section.lower() != "indigo" and section.lower() != "domoticz" and section[0] != DISABLE_CHARACTER:
			device_count += 1
			devices[str(device_count)] = {'control':config.get(section,"control"),'on':config.get(section,"on"),
									'off':config.get(section,"off"),
									'dim':config.get(section,'dim'),
									'id':generate_unique_id(section),
									'name': section,
									'number':device_count,
									'defined':my_name}
			hue_devices[str(device_count)] = {"state":{"on": False, "bri": 255, "hue": 14924, "sat": 143,"effect":"none",
												"xy":[0.4589,0.4103],"ct":365,"alert":"none","colormode":"hs",
												"reachable":True}, "type":"Extended color light","name":section,"modelid":"LCT001",
												"manufacturername":"Philips","uniqueid":generate_unique_id(section),
												"swversion": "66010820", "pointsymbol": { "1":"none", "2":"none", 
												"3":"none", "4":"none", "5":"none", "6":"none", "7":"none", "8":"none" }}
												
	local_devices = devices
	print "Loaded "+str(len(local_devices))+" devices from config file."
	
