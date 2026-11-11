#!/usr/bin/env bash
export $(grep -v '^#' .env | xargs)

FILE="docker-compose-qgis.yml"

docker compose -f ${FILE} up -d --force-recreate --remove-orphans
echo "Wait 10 seconds"
sleep 10
echo "Containers are running"
