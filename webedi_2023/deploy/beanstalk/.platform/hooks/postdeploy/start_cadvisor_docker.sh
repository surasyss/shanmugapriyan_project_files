#!/bin/bash

sudo docker rm -f cadvisor
sudo docker run -d --restart always --name cadvisor -p 8080:8080 -v "/:/rootfs:ro" -v "/var/run:/var/run:rw" -v "/sys:/sys:ro" -v "/var/lib/docker:/var/lib/docker:ro" 767512458197.dkr.ecr.us-east-1.amazonaws.com/plateiq/cadvisor:v0.40.0
