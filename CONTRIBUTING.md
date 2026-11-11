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
* For tests, they are written with `unittest` and launched with `pytest`.
  The QGIS application, a fake `iface` and the Processing provider are set up in `QuickOSM/test/conftest.py`.
  * They are launched on GitHub Actions, you can check the [CI status](https://github.com/QuickOSM/QuickOSM/actions/workflows/ci.yml) on each commits and pull requests.
  * You can launch them locally:
     * `make tests` using Docker, with QGIS 3.40 by default.
        * Another QGIS version can be used, with any `qgis/qgis` tag available on [Docker Hub](https://hub.docker.com/r/qgis/qgis/tags): `make tests QGIS_VERSION=3.44` or `make tests QGIS_VERSION=4.2`.
        * Or step by step: `make start_tests`, then `make run_tests` as many times as needed, then `make stop_tests`.
        * Extra pytest arguments can be given: `cd .docker && ./exec.sh -k processing`.
        * If you are using docker, do not forget to update your image from time to time `docker pull qgis/qgis:latest`.
     * With `python3 -m pytest QuickOSM/test`, from a Python environment where `qgis` and `processing` can be imported.
     * From QGIS Desktop, in the Python console, if `pytest` is installed in the QGIS Python environment:

```python
from qgis.utils import plugins
plugins['QuickOSM'].run_tests()  # or run_tests('-k', 'processing')
```

  * Some tests are using internet (Nominatim, Overpass), they can fail if these servers are down.

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
