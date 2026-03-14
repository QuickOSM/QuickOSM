"""OSM Parser file."""
import logging

from os.path import basename, dirname, isfile, join, realpath
from typing import List

import processing

from osgeo import gdal
from qgis.core import (
    QgsField,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QObject, QVariant, pyqtSignal

from QuickOSM.core.exceptions import FileOutPutException, QuickOsmException
from QuickOSM.core.utilities.tools import check_processing_enable
from QuickOSM.definitions.format import Format
from QuickOSM.definitions.osm import WHITE_LIST, Osm_Layers
from QuickOSM.tools.i18n import tr


LOGGER = logging.getLogger('QuickOSM')


class OsmParser(QObject):

    """
    Parse an OSM file with OGR.
    """

    # Signal percentage
    signalPercentage = pyqtSignal(int, name='signalPercentage')
    # Signal text
    signalText = pyqtSignal(str, name='signalText')

    # Dict to build the full ID of an object
    DIC_OSM_TYPE = {'node': 'n', 'way': 'w', 'relation': 'r'}

    def __init__(
            self,
            osm_file: str,
            layers: List[str] = None,
            output_format: Format = None,
            output_dir: str = None,
            prefix_file: str = None,
            layer_name: str = None,
            white_list_column: dict = None,
            key: List[str] = None,
            delete_empty_layers: bool = False,
            load_only: bool = False,
            osm_conf: str = None,
            subset: bool = False,
            subset_query: str = None,
            feedback_alg: bool = False,
            feedback: QgsProcessingFeedback = None):
        self.__osmFile = osm_file
        if layers is None:
            self.__layers = Osm_Layers
        else:
            self.__layers = layers

        self.__output_format = output_format
        self.__output_dir = output_dir
        self.__prefix_file = prefix_file
        self.__layer_name = layer_name

        if white_list_column is None:
            self.__whiteListColumn = WHITE_LIST
        else:
            self.__whiteListColumn = white_list_column
        self.__key = key if key is not None else []
        self.__deleteEmptyLayers = delete_empty_layers
        self.__loadOnly = load_only

        # If an osm_conf is provided ?
        if not osm_conf:
            current_dir = dirname(realpath(__file__))
            self._osm_conf = join(current_dir, 'QuickOSMconf.ini')
        else:
            self._osm_conf = osm_conf

        self.__subset = subset
        self.__subset_query = subset_query
        self.feedback_alg = feedback_alg
        self.feedback = feedback

        QObject.__init__(self)

    def processing_parse(self):
        """
        Start parsing the osm file with processing.
        """

        # Configuration for OGR
        gdal.SetConfigOption('OSM_CONFIG_FILE', self._osm_conf)
        gdal.SetConfigOption('OSM_USE_CUSTOM_INDEXING', 'NO')

        if not isfile(self.__osmFile):
            raise QuickOsmException(tr('File does not exist'))

        uri = self.__osmFile + "|layername="
        layers = {}

        # If loadOnly, no parsing required:
        # It's used only when we ask to open an osm file
        if self.__loadOnly:
            file_name = basename(self.__osmFile)
            for layer in self.__layers:
                layers[layer] = QgsVectorLayer(
                    uri + layer, file_name + ' ' + layer, 'ogr')

                if not layers[layer].isValid():
                    message = tr('Error on the layer : {layer} is not valid.').format(layer=layer)
                    raise QuickOsmException(message)

            return layers

        # Foreach layers
        for k, layer in enumerate(self.__layers):
            self.signalText.emit(tr('Parsing layer : {layer}').format(layer=layer))
            layers[layer] = {}

            # Reading it with a QgsVectorLayer
            layers[layer]['vectorLayer'] = QgsVectorLayer(
                uri + layer, 'test_' + layer, 'ogr')

            if not layers[layer]['vectorLayer'].isValid():
                message = f'Error on the layer : {layer} is not valid.'
                raise QuickOsmException(message)

            if self.feedback_alg:
                self.feedback.pushInfo(f'Checking the validity of the geometry of the layer {layer}.')

            # Let's check again Processing...
            # Checking again at the opening of the dialog is not enough according to GH tickets
            # https://github.com/QuickOSM/QuickOSM/issues/422
            flag, _, error = check_processing_enable()
            if not flag:
                raise QgsProcessingException(error)

            validity = processing.run(
                "qgis:checkvalidity", {
                    'INPUT_LAYER': layers[layer]['vectorLayer'],
                    'METHOD': 2,  # GEOS
                    'IGNORE_RING_SELF_INTERSECTION': False,
                    'VALID_OUTPUT': 'TEMPORARY_OUTPUT',
                    'INVALID_OUTPUT': 'TEMPORARY_OUTPUT',
                    'ERROR_OUTPUT': 'TEMPORARY_OUTPUT'
                }, feedback=self.feedback if self.feedback_alg else None
            )
            if validity['INVALID_COUNT'] > 0:
                LOGGER.info(f'Fixing geometries in layer: {layer}')
                if self.feedback_alg:
                    self.feedback.pushInfo(f'Fixing the geometry of the layer {layer}.')
                layers[layer]['vectorLayer'] = processing.run(
                    "native:fixgeometries", {
                        'INPUT': layers[layer]['vectorLayer'],
                        'OUTPUT': 'TEMPORARY_OUTPUT'
                    }, feedback=self.feedback if self.feedback_alg else None
                )['OUTPUT']

            layers[layer]['vectorLayer'].setProviderEncoding('UTF-8')

            # Save the geometry type of the layer
            layers[layer]['geomType'] = layers[layer]['vectorLayer'].wkbType()

            # Set a featureCount
            layers[layer]['featureCount'] = 0

            # Set expected fields
            expected_fields = self.__whiteListColumn[layer] if self.__whiteListColumn[layer] else ''

            # Get the other_tags
            if self.feedback_alg:
                self.feedback.setCurrentStep(2 + k)
                self.feedback.pushInfo(f'Explode the other_tags field in layer {layer}.')
            if self.feedback:
                if self.feedback.isCanceled():
                    return None
            layers[layer]['vector_layer'] = processing.run(
                "native:explodehstorefield", {
                    'INPUT': layers[layer]['vectorLayer'],
                    'FIELD': 'other_tags', 'EXPECTED_FIELDS': expected_fields,
                    'OUTPUT': 'TEMPORARY_OUTPUT'
                }, feedback=self.feedback if self.feedback_alg else None
            )['OUTPUT']
            if self.__subset:
                LOGGER.info(f'Subset filter: {self.__subset_query}')
                layers[layer]['vector_layer'].setSubsetString(self.__subset_query)

            layers[layer]['vector_layer'].startEditing()
            layer_provider = layers[layer]['vector_layer'].dataProvider()

            fields = layers[layer]['vector_layer'].fields()
            layer_provider.deleteAttributes([fields.indexOf('other_tags')])
            layer_provider.addAttributes([QgsField('osm_type', QVariant.String)])
            layer_provider.addAttributes([QgsField('full_id', QVariant.String)])
            layers[layer]['vector_layer'].updateFields()

            fields = layers[layer]['vector_layer'].fields()
            if self.__subset:
                # null_fields is a list of the empty field
                null_fields = fields.names()[:-2]
            features = layers[layer]['vector_layer'].getFeatures()
            meta = False
            for feature in features:
                if self.feedback_alg:
                    self.feedback.setCurrentStep(2)
                if self.feedback:
                    if self.feedback.isCanceled():
                        return None

                layers[layer]['featureCount'] += 1
                attributes = feature.attributes()
                index_version = fields.indexOf('osm_version')
                if attributes[index_version]:
                    meta = True

                id_f = feature.id()
                index = fields.indexOf('osm_id')
                index_ot = fields.indexOf('osm_type')
                index_fi = fields.indexOf('full_id')
                if layer in ['points', 'lines', 'multilinestrings']:
                    if layer == 'points':
                        osm_type = 'node'
                    elif layer == 'lines':
                        osm_type = 'way'
                    elif layer == 'multilinestrings':
                        osm_type = 'relation'
                    attr_value_fi = {index_fi: self.DIC_OSM_TYPE[osm_type] + str(attributes[index])}
                elif layer == 'multipolygons':
                    if attributes[index]:
                        osm_type = 'relation'
                        attr_value_fi = {index_fi: self.DIC_OSM_TYPE[osm_type] + str(attributes[index])}
                    else:
                        osm_type = 'way'
                        index_way = fields.indexOf('osm_way_id')
                        attr_value_fi = {index_fi: self.DIC_OSM_TYPE[osm_type] + str(attributes[index_way])}
                        layer_provider.changeAttributeValues(
                            {id_f: {index: str(attributes[index_way])}}
                        )
                attr_value_ot = {index_ot: osm_type}
                layer_provider.changeAttributeValues({id_f: attr_value_ot})

                layer_provider.changeAttributeValues({id_f: attr_value_fi})

                if self.__subset:
                    for field in null_fields:
                        index = fields.indexOf(field)
                        if attributes[index]:
                            index = null_fields.index(field)
                            null_fields.pop(index)

            if self.__subset:
                # delete empty fields
                null_index = [fields.indexOf(field) for field in null_fields]
                layer_provider.deleteAttributes(null_index)
                layers[layer]['vector_layer'].updateFields()

            layers[layer]['vector_layer'].commitChanges()

            if layers[layer]['featureCount']:
                if self.__output_dir:
                    if not self.__prefix_file:
                        self.__prefix_file = self.__layer_name

                    if self.__output_format in [Format.GeoPackage, Format.Kml]:
                        output_file = join(
                            self.__output_dir,
                            self.__prefix_file + "." + self.__output_format.value.extension)
                        final_name = self.__prefix_file + '_' + layer
                        layers[layer]['layer_name'] = f'ogr:dbname=\'{output_file}\' table=\"{final_name}\" (geom)'
                    elif self.__output_format in [Format.GeoJSON, Format.Shapefile]:
                        layers[layer]['layer_name'] = join(
                            self.__output_dir,
                            self.__prefix_file + "_" + layer + "." + self.__output_format.value.extension)
                    else:
                        raise NotImplementedError

                    if isfile(layers[layer]['layer_name']):
                        raise FileOutPutException(suffix='(' + layers[layer]['layer_name'] + ')')
                else:
                    layers[layer]['layer_name'] = 'TEMPORARY_OUTPUT'

                tags = layers[layer]['vector_layer'].fields().names()

                fields_mapping = [
                    {'expression': '\"full_id\"', 'length': 0, 'name': 'full_id', 'precision': 0, 'type': 10},
                    {'expression': '\"osm_id\"', 'length': 0, 'name': 'osm_id', 'precision': 0, 'type': 10},
                ]
                begin = 1
                nb_metadata = 5
                if layer == 'multipolygons':
                    begin += 1
                fields_mapping.append({
                    'expression': '\"osm_type\"', 'length': 0,
                    'name': 'osm_type', 'precision': 0, 'type': 10
                })
                if meta:
                    for name in tags[begin:begin + nb_metadata]:
                        fields_mapping.append({
                            'expression': '\"' + name + '\"',
                            'length': 0, 'name': name,
                            'precision': 0, 'type': 10
                        })
                begin += nb_metadata

                for key in list(set(self.__key)):
                    if key in tags:
                        fields_mapping.append({
                            'expression': '\"' + key + '\"',
                            'length': 0, 'name': key,
                            'precision': 0, 'type': 10
                        })

                for name in tags[begin:-2]:
                    if name not in self.__key:
                        fields_mapping.append({
                            'expression': '\"' + name + '\"',
                            'length': 0, 'name': name,
                            'precision': 0, 'type': 10
                        })

                layers[layer]['vector_layer'] = processing.run("native:refactorfields", {
                    'INPUT': layers[layer]['vector_layer'],
                    'FIELDS_MAPPING': fields_mapping,
                    'OUTPUT': layers[layer]['layer_name']
                }, feedback=self.feedback if self.feedback_alg else None)['OUTPUT']

                if self.__output_dir:
                    layers[layer]['vector_layer'] = QgsVectorLayer(
                        layers[layer]['vector_layer'], self.__prefix_file + "_" + layer, 'ogr'
                    )

                fields = layers[layer]['vector_layer'].fields()
                layers[layer]['tags'] = fields.names()

        return layers
