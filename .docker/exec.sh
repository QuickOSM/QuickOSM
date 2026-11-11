#!/usr/bin/env bash
export $(grep -v '^#' .env | xargs)

docker exec -t qgis sh -c "python3 -m pytest --version > /dev/null 2>&1 || pip3 install --break-system-packages pytest || pip3 install pytest"

docker exec -t -e QT_QPA_PLATFORM=offscreen qgis sh \
  -c "cd /tests_directory && python3 -m pytest ${PLUGIN_NAME}/test -v $*"
