#!/usr/bin/env bash
export $(grep -v '^#' .env | xargs)

FILE="docker-compose-qgis.yml"

docker compose -f ${FILE} up -d --force-recreate --remove-orphans
echo "Wait 10 seconds"
sleep 10
# qgis_setup.sh is only available in the "release-*" images, it's not needed by pytest
if docker exec qgis sh -c "command -v qgis_setup.sh" > /dev/null; then
  echo "Installation of the plugin ${PLUGIN_NAME}"
  docker exec -t qgis sh -c "qgis_setup.sh ${PLUGIN_NAME}"
fi
echo "Containers are running"
