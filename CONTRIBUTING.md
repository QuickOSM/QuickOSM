# Contributing

This project is hosted on GitHub.

[Visit GitHub](https://github.com/QuickOSM/QuickOSM/){: .md-button .md-button--primary }

## Scripts

We provide a Makefile which helps the developers to:

* run tests,
* build the documentation (Processing algorithms)

## Translation

The UI is available on [Transifex](https://www.transifex.com/quickosm/gui/), no development
knowledge is required. [![Transifex 🗺](https://github.com/QuickOSM/QuickOSM/actions/workflows/transifex.yml/badge.svg)](https://github.com/QuickOSM/QuickOSM/actions/workflows/transifex.yml)

## Code

SQL and Python are covered by unittests with Docker.

[![Tests 🎳](https://github.com/QuickOSM/QuickOSM/actions/workflows/ci.yml/badge.svg)](https://github.com/QuickOSM/QuickOSM/actions/workflows/ci.yml)

```bash
pip install -r requirements/dev.txt
flake8
make tests
```

* For panels, you can find a quick diagram in the `doc` folder.
* For tests, it's using the `unittest` framework.
  * They are launched on GitHub using Travis, you can check the [Travis status](https://travis-ci.org/3liz/QuickOSM) on each commits and pull requests.
  * You can launch them locally:
     * `make docker_test` using Docker with the current LTR following the [QGIS release schedule](https://www.qgis.org/en/site/getinvolved/development/roadmap.html#release-schedule).
        * `qgis_plugin_tools/docker_test.sh QuickOSM release-3_4` for QGIS 3.4
        * `qgis_plugin_tools/docker_test.sh QuickOSM latest` for QGIS Master or any other tags available on [Docker Hub](https://hub.docker.com/r/qgis/qgis/tags).
        * If you are using docker, do not forget to update your image from time to time `docker pull qgis/qgis:latest`.
     * Setting up your IDE to launch them by adding paths to your QGIS installation. I personally use PyCharm on Ubuntu.
     * Launching tests from QGIS Desktop app, in the Python console using :

```python
from qgis.utils import plugins
plugins['QuickOSM'].run_tests()
```

## Documentation

[![Documentation 📚](https://github.com/QuickOSM/QuickOSM/actions/workflows/publish-doc.yml/badge.svg)](https://github.com/QuickOSM/QuickOSM/actions/workflows/publish-doc.yml)

The documentation is using [MkDocs](https://www.mkdocs.org/) with [Material](https://squidfunk.github.io/mkdocs-material/) :

```bash
pip install -r requirements/doc.txt
mkdocs serve
```

* Processing algorithms documentation can be generated with:

```bash
make processing-doc
```
