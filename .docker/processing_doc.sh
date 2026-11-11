#!/usr/bin/env bash
# Generate the Processing documentation in docs/processing, used by the mkdocs website.
# QGIS 4.2 minimum, e.g. ./processing_doc.sh or QGIS_VERSION=4.4 ./processing_doc.sh
set -e

export $(grep -v '^#' .env | xargs)

QGIS_VERSION=${QGIS_VERSION:-4.2}
CONTAINER=qgis-processing-doc

docker run -d -t \
  --name ${CONTAINER} \
  -v "$(pwd)/../${PLUGIN_NAME}:/tests_directory/${PLUGIN_NAME}" \
  -v "$(pwd)/processing_doc.py:/processing_doc.py:ro" \
  -v "$(pwd)/../docs/processing:/output" \
  -e QT_QPA_PLATFORM=offscreen \
  qgis/qgis:${QGIS_VERSION}

trap 'docker rm -f ${CONTAINER} > /dev/null' EXIT

echo "Generating the Processing documentation with QGIS ${QGIS_VERSION}"
docker exec -t ${CONTAINER} sh -c 'PYTHONPATH=/tests_directory:${PYTHONPATH} python3 /processing_doc.py /output'

# Files are written by root in the container
docker exec -t ${CONTAINER} chown -R "$(id -u):$(id -g)" /output
