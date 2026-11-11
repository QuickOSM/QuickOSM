#!/usr/bin/env bash
export $(grep -v '^#' .env | xargs)

#xhost +

docker run -d -t \
  --name qgis-testing-environment \
  -v  $(pwd)/../:/plugin \
  -e DISPLAY=:99 \
  qgis/qgis:3.40

sleep 10

echo "Setting up"
docker exec -t qgis-testing-environment sh -c "cd /plugin && cp CHANGELOG.md docs/"
docker exec -t qgis-testing-environment sh -c "cd /plugin && cp CONTRIBUTING.md docs/"
docker exec -t qgis-testing-environment sh -c "python3 -m pip install --break-system-packages --ignore-installed -r /plugin/requirements/doc.txt"
docker exec -t qgis-testing-environment sh -c "cd /plugin && mkdocs gh-deploy --clean --force --verbose"

docker kill qgis-testing-environment
docker rm qgis-testing-environment
