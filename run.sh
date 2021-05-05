#!/bin/bash
docker rm -f icsbot
docker run -d --name icsbot -p 5000:5000 -e PROJECTID=$1 -v $2/icsbotsa.json:/usr/src/app/icsbotsa.json -v $2/icsbot-firebase.json:/usr/src/app/icsbot-firebase.json icsbot
docker logs -f icsbot