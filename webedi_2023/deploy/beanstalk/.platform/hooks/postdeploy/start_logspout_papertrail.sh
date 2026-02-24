#!/bin/bash

START_LOGSPOUT="${START_LOGSPOUT:-0}"
APP_NAME="${APP_NAME:-${SERVER_CONFIG}}"

if [ "$START_LOGSPOUT" != "0" ]; then
	PAPERTRAIL_ADDRESS="${PAPERTRAIL_ADDRESS:-logs7.papertrailapp.com:27050}"
	sudo docker rm -f logspout
	sudo docker run --restart=always -d -e SYSLOG_HOSTNAME="$APP_NAME" --name="logspout" --volume=/var/run/docker.sock:/var/run/docker.sock 767512458197.dkr.ecr.us-east-1.amazonaws.com/plateiq/logspout:latest syslog+tls://"$PAPERTRAIL_ADDRESS"
fi
