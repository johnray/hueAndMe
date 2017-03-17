#!/bin/bash
nohup /bin/java -Dserver.port=8081 -jar /home/pi/habridge/ha-bridge-3.5.1.jar > /home/pi/habridge/habridge-log.txt 2>&1 &
