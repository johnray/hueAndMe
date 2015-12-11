#Filehandler config file (shared with main config)
CONFIG_FILE = "hueAndMe.cfg"
INDIGO_REALM="Indigo Control Server"
MAX_DEVICES=25
EXCLUSION_DELIMITER='"'

import hashlib
import ConfigParser
import re
import urllib2
import json
import time

local_devices = {}
INDIGO_USER = ""
INDIGO_PASS = ""

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
	global CONFIG_FILE, INDIGO_REALM, INDIGO_USER, INDIGO_PASS
	authhandler = urllib2.HTTPDigestAuthHandler()
	authhandler.add_password(INDIGO_REALM, url, INDIGO_USER, INDIGO_PASS)
	opener = urllib2.build_opener(authhandler)
	urllib2.install_opener(opener)
	response = urllib2.urlopen(url)
	trash = response.read()


def load_devices(devices, hue_devices):
	global CONFIG_FILE, INDIGO_REALM, MAX_DEVICES, EXCLUSION_DELIMITER, local_devices, INDIGO_USER, INDIGO_PASS
	my_name = re.sub(r'.*?\.', r'', __name__)
	indigoconfig = ConfigParser.SafeConfigParser()
	indigoconfig.read(CONFIG_FILE)
	device_count = len(devices)-1
	internal_count = 0
	# Read config items
	INDIGO_BASE_URL = indigoconfig.get('indigo','base_url')
	INDIGO_USER = indigoconfig.get('indigo','username')
	INDIGO_PASS = indigoconfig.get('indigo','password')
	EXCLUSIONS = indigoconfig.get('indigo','exclusions')
	INDIGO_DEVICES_URL = INDIGO_BASE_URL+"/devices.json/"

	# Read Indigo device list 
	authhandler = urllib2.HTTPDigestAuthHandler()
	authhandler.add_password(INDIGO_REALM, INDIGO_DEVICES_URL, INDIGO_USER, INDIGO_PASS)
	opener = urllib2.build_opener(authhandler)
	urllib2.install_opener(opener)
	response = urllib2.urlopen(INDIGO_DEVICES_URL)
	indigo_devices = response.read()
	# My indigo JSON device list is invalid. This regex fixes it.
	indigo_devices = re.sub(r'\[\s*\,', r'[', indigo_devices)  #]
	indigo_devices = json.loads(indigo_devices)
	
	# Parse Indigo device list into devices and hue devices
	for device in indigo_devices:
		device_count += 1
		internal_count += 1
		if internal_count <= MAX_DEVICES and (EXCLUSION_DELIMITER+device['name']+EXCLUSION_DELIMITER not in EXCLUSIONS):
			devices[str(device_count)] = {'control':'url','on':INDIGO_BASE_URL+device['restURL']+"?isOn=1&_method=put",
								'off':INDIGO_BASE_URL+device['restURL']+"?isOn=0&_method=put",
								'dim':INDIGO_BASE_URL+device['restURL']+"?brightness={dim}&_method=put",
								'id':generate_unique_id(device['name']),
								'name':device['name'].encode('ascii', 'ignore'),
								'number':device_count,
								'dimlevel':0,
								'defined':my_name}
			hue_devices[str(device_count)] = {"state":{"on": False, "bri": 255, "hue": 14924, "sat": 143,"effect":"none",
								"xy":[0.4589,0.4103],"ct":365,"alert":"none","colormode":"hs",
								"reachable":True}, "type":"Extended color light","name":device['name'].encode('ascii', 'ignore'),"modelid":"LCT001",
								"manufacturername":"Philips","uniqueid":generate_unique_id(device['name'].encode('ascii', 'ignore')),
								"swversion": "66010820", "pointsymbol": { "1":"none", "2":"none", 
								"3":"none", "4":"none", "5":"none", "6":"none", "7":"none", "8":"none" }}
								
	local_devices = devices
	print "Loaded "+str(len(local_devices))+" devices from Indigo."
	
	
