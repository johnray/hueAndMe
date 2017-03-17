#!/usr/bin/python
#config
CONFIG_FILE = "hueAndMe.cfg"

import socket
import time
import SocketServer
import re
import os.path
import sys
import mimetypes
import time
import json
from threading import Thread
import ConfigParser

RESOURCES_PATH = "resources"
BCAST_IP = "239.255.255.250"
UPNP_PORT = 1900
BROADCAST_INTERVAL = 10 # Seconds between upnp broadcast
M_SEARCH_REQ_MATCH = "M-SEARCH"

mainconfig = ConfigParser.SafeConfigParser()
mainconfig.read(CONFIG_FILE)

# Read config items
IP = mainconfig.get('general','server_ip')
if IP == "guess":
	IP = socket.gethostbyname(socket.gethostname())
HTTP_PORT = mainconfig.getint('general','server_port')

if mainconfig.getboolean('general','load_file'):
	from devicehandlers import fileconfig

if mainconfig.getboolean('general','load_indigo'):
	from devicehandlers import indigoconfig

if mainconfig.getboolean('general','load_domoticz'):
	from devicehandlers import domoticz

class Broadcaster(Thread):
	interrupted = False
	def run(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 20)
		
		while True:
			sock.sendto(UPNP_BROADCAST, (BCAST_IP, UPNP_PORT))
			for x in range(BROADCAST_INTERVAL):
				time.sleep(1)
				if self.interrupted:
					sock.close()
					return

	def stop(self):
		self.interrupted = True
 
class Responder(Thread):
	interrupted = False
	def run(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,socket.IPPROTO_UDP)
		sock.bind(('', UPNP_PORT))
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(BCAST_IP) + socket.inet_aton(IP));
		sock.settimeout(1)
	 	while True:
			try:
				data, addr = sock.recvfrom(1024)
			except socket.error:
				if self.interrupted:
					sock.close()
					return
			else:
				#print data
				if M_SEARCH_REQ_MATCH in data:
					#print "received M-SEARCH from ", addr, "\n", data
					self.respond(addr)
		

	def stop(self):
		self.interrupted = True

	def respond(self, addr):
		outSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		outSock.sendto(UPNP_RESPONSE, addr)
		outSock.close()
		#print "UDP Response sent to ",addr,"\n"

class Httpd(Thread):
	def run(self):
		self.server = SocketServer.ThreadingTCPServer((IP, HTTP_PORT), HttpdRequestHandler)
		self.server.allow_reuse_address = True
		self.server.serve_forever()	

	def stop(self):
		self.server.shutdown()

class HueResponseGenerator(object):		
	@classmethod
	def perform_substitutions(cls,original):
		original=original.replace("{ip}",IP)
		original=original.replace("{port}",str(HTTP_PORT))
		original=original.replace("{currentdatetime}",time.strftime("%Y-%m-%dT%H:%M:%S"))
		return original
	
	@classmethod	
	def get_response(cls,request_string):
		
		# get device list
		get_match = re.search(r'(\/[^\s^\/]+)$',request_string)
		if get_match:
			request_file=get_match.group(1)
		else:
			request_file=""
		if request_file == "" or request_file == "/":
			request_file = "/index.html"
		#print "Get request: "+request_string+", just the file: "+request_file
		if re.search(r'/lights$',request_string):
			print "Discovery request"
			return json.dumps(hue_devices)
		
		# Get individual device status
		get_device_match = re.search(r'/lights/([0-9]+)$',request_string)
		if get_device_match:
			return json.dumps(hue_devices[str(get_device_match.group(1))])
		elif re.search(r'/api/[^\/]+$',request_string):
			#print "full request"
			return "{}"
		elif os.path.exists(RESOURCES_PATH+request_file):
				#print "serving from a local file"
				with open (RESOURCES_PATH+request_file, "r") as datafile:
					send_data=datafile.read()
					send_data = HueResponseGenerator.perform_substitutions(send_data)
					return send_data
		else:
			return "{}"
	
	@classmethod
	def put_response(cls,request_string,request_data):
		#print "REQUEST STRING==="+request_string+"===="
		put_device_match = re.search(r'/lights/([0-9]+)/state$',request_string)
		if put_device_match:
			device = put_device_match.group(1)
			request = json.loads(request_data)
			#print request
			list = []
			for key in request:
				# Do something for each key here, then return success
				list.append({"success":{key:request[key]}})
				#print "Key=="+key
				if key.lower() == "on":
					# Do nothing ON == TRUE, OFF == FALSE
					if request[key] == True:
						print "Turn On "+devices[device]['name']
						execute_string = devices[device]['defined']+".on('"+device+"')"
						#print execute_string
						eval(execute_string)
					else:
						print "Turn Off "+devices[device]['name']
						execute_string = devices[device]['defined']+".off('"+device+"')"
						#print execute_string
						eval(execute_string)
				if key.lower() == "bri":
					print "Bright/Dim "+str(request[key])+", "+devices[device]['name']
					execute_string = devices[device]['defined']+".dim('"+device+"',"+str(request[key])+")"
					#print execute_string
					eval(execute_string)
			return json.dumps(list)


class HttpdRequestHandler(SocketServer.BaseRequestHandler ):
	def handle(self):
		data = self.request.recv(1024)
		get_match = re.search(r'GET (.*?(\/[^\s^\/]*?))\s',data)
		if get_match:
			get_request_full=get_match.group(1).replace("..","")
			self.send_headers(get_request_full)
			self.request.sendall(HueResponseGenerator().get_response(get_request_full))
		put_match = re.search(r'PUT (.*?(\/[^\s^\/]*?))\s',data)
		put_data_match = re.search(r'(\{.*\})',data)
		if put_match and put_data_match:
			put_request_full = put_match.group(1).replace("..","")
			put_data = put_data_match.group(1)
			#print "PUT request: "+put_request_full
			#print "PUT data: "+put_data
			self.send_headers("file.json")
			self.request.sendall(HueResponseGenerator().put_response(put_request_full,put_data))
						
	def send_headers(self,file):
		self.request.sendall("HTTP/1.1 200 OK\r\n")
		self.request.sendall("Cache-Control: no-store, no-cache, must-revalidate, post-check=0, pre-check=0\r\n")
		(type,encoding) = mimetypes.guess_type(file)
		if type is None:
			type = "application/json"
		self.request.sendall("Content-type: "+type+"\r\n\r\n")
		#print "Sent content type: "+type




with open (RESOURCES_PATH+"/broadcast_packet.txt", "r") as datafile: 
	UPNP_BROADCAST = datafile.read()
	UPNP_BROADCAST = HueResponseGenerator.perform_substitutions(UPNP_BROADCAST)

with open (RESOURCES_PATH+"/response_packet.txt", "r") as datafile: 
	UPNP_RESPONSE = datafile.read()
	UPNP_RESPONSE = HueResponseGenerator.perform_substitutions(UPNP_RESPONSE)

	
if __name__ == '__main__':
	mimetypes.init()
	devices = {}
	hue_devices = {}
	device_count = 0
	# hue_devices is for hue specific information - I can use it to generate a response directly to the requestor
	# devices is my internal representation of a device - It's kept separate for that reason
	
	mainconfig = ConfigParser.SafeConfigParser()
	mainconfig.read(CONFIG_FILE)

	if mainconfig.getboolean('general','load_file'):
		fileconfig.load_devices(devices,hue_devices)
		
	if mainconfig.getboolean('general','load_indigo'):
		indigoconfig.load_devices(devices,hue_devices)
	
	if mainconfig.getboolean('general','load_domoticz'):
		domoticz.load_devices(devices,hue_devices)
		
	responder = Responder()
	broadcaster = Broadcaster()
	httpd = Httpd()
	responder.start()
	broadcaster.start()
	httpd.start()
	try:
		while True:
			responder.join(1)
			broadcaster.join(1)
			httpd.join(1)
	except (KeyboardInterrupt, SystemExit):
		print "Exiting"
	responder.stop()
	broadcaster.stop()
	httpd.stop()


