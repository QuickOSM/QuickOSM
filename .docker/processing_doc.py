"""Generate the Processing documentation, docs/processing/README.md, and the screenshots.

It's launched by processing_doc.sh, in the qgis/qgis Docker image.
QGIS 4.2 minimum.
"""

import sys

from pathlib import Path
from unittest import mock

import qgis.utils

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsProcessing,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber,
    QgsProcessingParameterVectorLayer,
)
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import QObject
from qgis.testing import start_app

OUTPUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/output')

TEMPLATE = """---
hide:
  - navigation
---

# Processing
"""

TEMPLATE_GROUP = """
## {group}

"""

TEMPLATE_ALGORITHM = """
### {title}

{help_string}

![algo_id]({img})

#### Parameters

| ID | Description | Type | Info | Required | Advanced | Option |
|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
{parameters}

#### Outputs

| ID | Description | Type | Info |
|:-:|:-:|:-:|:-:|
{outputs}

***

"""

TEMPLATE_FOOTER = """
*Documentation generated with QGIS {version}.*
"""

TEMPLATE_PARAMETERS = '{id}|{description}|{type}|{info}|{required}|{advanced}|{option}|\n'

TEMPLATE_OUTPUT = '{id}|{description}|{type}|{info}|\n'


class FakeIface(QObject):
    """Minimal iface, enough to open the algorithm dialogs."""

    def __init__(self):
        super().__init__()
        self._canvas = QgsMapCanvas()

    def mapCanvas(self):  # NOQA N802
        """Return the map canvas."""
        return self._canvas

    def mainWindow(self):  # NOQA N802
        """No main window, dialogs are opened without a parent."""
        return None

    def browserModel(self):  # NOQA N802
        """No browser model, it's optional for the parameter widgets."""
        return None

    def activeLayer(self):  # NOQA N802
        """No active layer."""
        return None

    def __getattr__(self, name):
        value = mock.MagicMock(name=f'iface.{name}')
        setattr(self, name, value)
        return value


def format_type(class_name: str) -> str:
    """Short name of a parameter or an output class."""
    class_name = class_name.replace('QgsProcessingParameter', '')
    return class_name.replace('QgsProcessingOutput', '')


def format_number(value: float) -> str:
    """Display integers without decimals."""
    return str(int(value)) if float(value).is_integer() else str(value)


def parameter_option(param) -> str:
    """Default value and constraints of a parameter."""
    option = ''
    if param.defaultValue():
        option += f'Default: {param.defaultValue()} <br> '

    if isinstance(param, QgsProcessingParameterNumber):
        if param.dataType() == Qgis.ProcessingNumberParameterType.Double:
            option += 'Type: Double<br> '
        else:
            option += 'Type: Integer<br> '
        limits = []
        # Unset limits are the extreme float values
        if param.minimum() and abs(param.minimum()) < sys.float_info.max:
            limits.append(f'Min: {format_number(param.minimum())}')
        if param.maximum() and abs(param.maximum()) < sys.float_info.max:
            limits.append(f'Max: {format_number(param.maximum())}')
        if limits:
            option += ', '.join(limits) + ' <br>'

    elif isinstance(param, QgsProcessingParameterVectorLayer):
        types = [QgsProcessing.sourceTypeToString(item) for item in param.dataTypes()]
        option += 'Type: ' + ', '.join(types) + ' <br>'

    elif isinstance(param, QgsProcessingParameterFeatureSink):
        option += 'Type: ' + QgsProcessing.sourceTypeToString(param.dataType()) + ' <br>'

    elif isinstance(param, QgsProcessingParameterEnum):
        option += 'Values: ' + ', '.join(param.options()) + ' <br>'

    return option


def screenshot(algorithm_id: str, output: Path):
    """Save a screenshot of the algorithm dialog."""
    from processing import createAlgorithmDialog

    dialog = createAlgorithmDialog(algorithm_id)
    dialog.resize(1100, 800)
    dialog.grab().save(str(output))
    dialog.deleteLater()


def generate_processing_doc(provider, output_dir: Path):
    """Write the README.md and the screenshots in the output directory."""
    algorithms_markdown = {}

    for alg in provider.algorithms():
        image = output_dir / '{}.png'.format(alg.id().replace(':', '-'))
        screenshot(alg.id(), image)

        param_markdown = ''
        for param in alg.parameterDefinitions():
            flags = param.flags()
            param_markdown += TEMPLATE_PARAMETERS.format(
                id=param.name(),
                type=format_type(param.__class__.__name__),
                description=param.description(),
                info=param.help() or '',
                required='' if flags & Qgis.ProcessingParameterFlag.Optional else '✓',
                advanced='✓' if flags & Qgis.ProcessingParameterFlag.Advanced else '',
                option=parameter_option(param),
            )

        output_markdown = ''
        for output in alg.outputDefinitions():
            output_markdown += TEMPLATE_OUTPUT.format(
                id=output.name(),
                type=format_type(output.__class__.__name__),
                description=output.description(),
                info='',
            )

        markdown = TEMPLATE_ALGORITHM.format(
            title=alg.displayName(),
            help_string=alg.shortHelpString() or '',
            parameters=param_markdown or 'No parameter',
            outputs=output_markdown or 'No output',
            img=f'./{image.name}',
        )
        algorithms_markdown.setdefault(alg.group(), []).append(markdown)

    markdown_all = TEMPLATE
    # Algorithms without a group first, they are the main ones
    groups = sorted(algorithms_markdown.items(), key=lambda item: bool(item[0]))
    for group, algorithms in groups:
        if group:
            markdown_all += TEMPLATE_GROUP.format(group=group)
        markdown_all += ''.join(algorithms)
    markdown_all += TEMPLATE_FOOTER.format(version=Qgis.version())

    (output_dir / 'README.md').write_text(markdown_all, encoding='utf-8')
    print(f'{len(provider.algorithms())} algorithms documented in {output_dir}')


def main():
    """Set up QGIS, Processing and the QuickOSM provider, then generate the doc."""
    if Qgis.QGIS_VERSION_INT < 40200:
        sys.exit(f'QGIS 4.2 minimum is required, found {Qgis.QGIS_VERSION}')

    app = start_app()  # NOQA F841
    qgis.utils.iface = FakeIface()

    try:
        import processing  # noqa: F401
    except ModuleNotFoundError:
        sys.path.append(str(Path(QgsApplication.pkgDataPath()) / 'python' / 'plugins'))

    from processing.core.Processing import Processing

    Processing.initialize()
    # QuickOSM checks that the Processing plugin is enabled.
    qgis.utils.plugins.setdefault('processing', mock.MagicMock())

    from QuickOSM.quick_osm_processing.provider import Provider

    provider = Provider()
    QgsApplication.processingRegistry().addProvider(provider)

    generate_processing_doc(provider, OUTPUT)


if __name__ == '__main__':
    main()
