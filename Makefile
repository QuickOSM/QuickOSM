# QGIS version used for tests, e.g. make tests QGIS_VERSION=4.2
QGIS_VERSION ?= 3.44
export QGIS_VERSION

start_tests:
	@echo "Start docker compose with QGIS $(QGIS_VERSION)"
	@cd .docker && ./start.sh

run_tests:
	@echo 'Running tests, containers must be running'
	@cd .docker && ./exec.sh

stop_tests:
	@echo 'Stopping/killing containers'
	@cd .docker && ./stop.sh

tests: start_tests run_tests stop_tests

processing-doc:
	cd .docker && ./processing_doc.sh

code-doc:
	cd .docker && ./code_doc.sh

lint:
	pre-commit run --all-files
