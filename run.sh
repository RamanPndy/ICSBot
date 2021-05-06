#!/bin/bash
docker rm -f icsbot
docker run -d --name icsbot -p 5000:5000 -e PROJECTID=$1 -e DBUSER=$2 -e DBPASS=$3 -v $4/icsbotsa.json:/usr/src/app/icsbotsa.json icsbot
docker logs -f icsbot