"""Manage the saved query in history or preset."""
import json
import logging
import os
import re
import shutil

from os import listdir, remove, rename
from os.path import join
from typing import List, Union

from qgis.core import QgsRectangle

from QuickOSM.core.utilities.json_encoder import EnumEncoder, as_enum
from QuickOSM.core.utilities.tools import query_historic, query_preset
from QuickOSM.definitions.format import Format
from QuickOSM.definitions.osm import (
    OSM_LAYERS,
    WHITE_LIST,
    LayerType,
    MultiType,
)
from QuickOSM.tools.i18n import tr


LOGGER = logging.getLogger('QuickOSM')


class QueryManagement:
    """Manage the saved query in history or preset."""

    def __init__(
            self,
            query: Union[str, List[str]] = '',
            name: str = '',
            description: Union[str, List[str]] = '',
            advanced: bool = False,
            type_multi_request: list = None,
            keys: Union[str, List[str]] = None,
            values: Union[str, List[str]] = None,
            area: Union[str, List[str]] = None,
            bbox: Union[QgsRectangle, List[QgsRectangle]] = None,
            output_geometry_types: list = None,
            white_list_column: dict = None,
            output_directory: str = None,
            output_format: Format = None
    ):
        """Constructor"""
        if isinstance(query, str):
            self.query = [query]
        else:
            self.query = query

        if isinstance(name, str):
            self.name = [name]
        else:
            self.name = name

        if description is None:
            self.description = ['']
        elif isinstance(description, str):
            self.description = [description]
        else:
            self.description = description

        self.advanced = advanced

        if type_multi_request is None:
            self.type_multi_request = [[]]
        elif isinstance(type_multi_request, MultiType):
            self.type_multi_request = [[type_multi_request]]
        elif not type_multi_request or isinstance(type_multi_request[0], MultiType):
            self.type_multi_request = [type_multi_request]
        else:
            self.type_multi_request = type_multi_request

        if keys is None:
            self.keys = [['']]
        elif isinstance(keys, str):
            self.keys = [[keys]]
        elif isinstance(keys[0], str):
            self.keys = [keys]
        else:
            self.keys = keys

        if values is None:
            self.values = [['']]
        elif isinstance(values, str):
            self.values = [[values]]
        elif isinstance(values[0], str):
            self.values = [values]
        else:
            self.values = values

        if area is None:
            self.area = ['']
        elif isinstance(area, str):
            self.area = [area]
        else:
            self.area = area

        if bbox is None:
            self.bbox = ['']
        elif isinstance(bbox, QgsRectangle):
            self.bbox = [bbox]
        elif isinstance(bbox, str):
            self.bbox = [bbox]
        else:
            self.bbox = bbox

        if output_geometry_types is None:
            self.output_geom_type = [OSM_LAYERS]
        elif isinstance(output_geometry_types[0], LayerType):
            self.output_geom_type = [output_geometry_types]
        else:
            self.output_geom_type = output_geometry_types

        if white_list_column is None:
            self.white_list = [WHITE_LIST]
        elif isinstance(white_list_column, dict):
            self.white_list = [white_list_column]
        else:
            self.white_list = white_list_column

        if output_directory is None:
            self.output_directory = ['']
        elif isinstance(output_directory, str):
            self.output_directory = [output_directory]
        else:
            self.output_directory = output_directory

        if output_format is None:
            self.output_format = ['']
        elif isinstance(output_format, Format):
            self.output_format = [output_format]
        else:
            self.output_format = output_format

    def write_query_historic(self):
        """Write new query in the history folder"""
        history_folder = query_historic()
        files = listdir(history_folder)
        nb_files = len(files)

        if nb_files == 10:
            remove(join(history_folder, 'query_saved_0.json'))
            files = listdir(history_folder)
            for k, file in enumerate(files):
                former_file = join(history_folder, file)
                new_file = join(history_folder, f'query_saved_{k}.json')
                rename(former_file, new_file)
            new_file = join(history_folder, f'query_saved_{nb_files - 1}.json')
        else:
            new_file = join(history_folder, f'query_saved_{nb_files}.json')

        self.write_json(new_file)

    def add_preset(self, name_preset: str):
        """Add a new query in the preset folder"""
        preset_folder = query_preset()
        files = listdir(preset_folder)
        nb_files = len(files)

        self.name[0] = name_preset if name_preset != "OsmQuery" else f'OsmQuery_{nb_files}'
        final_name = self.name[0] + '.json'

        new_file = join(preset_folder, self.name[0], final_name)
        os.mkdir(join(preset_folder, self.name[0]))
        self.write_json(new_file)

    def write_json(self, file: str):
        """Write the saved file in json"""
        data = {
            'query': self.query,
            'description': self.description,
            'advanced': self.advanced,
            'file_name': self.name[0],
            'query_layer_name': self.name,
            'query_name': [tr('Query') + '1'],
            'type_multi_request': self.type_multi_request,
            'keys': self.keys,
            'values': self.values,
            'area': self.area,
            'bbox': self.bbox,
            'output_geom_type': self.output_geom_type,
            'white_list_column': self.white_list,
            'output_directory': self.output_directory,
            'output_format': self.output_format
        }

        with open(file, 'w', encoding='utf8') as json_file:
            json.dump(data, json_file, cls=EnumEncoder)

    @staticmethod
    def remove_preset(name: str):
        """Remove a preset."""
        preset_folder = query_preset()

        dir_file = join(preset_folder, name)
        shutil.rmtree(dir_file)
        if name.startswith('OsmQuery_'):
            presets = os.listdir(preset_folder)
            list_preset = filter(lambda query_file: query_file.startswith('OsmQuery_'), presets)
            num = re.findall('OsmQuery_([0-9]+)', name)[0]
            for k, file in enumerate(list_preset):
                if k >= num:
                    former_file = join(preset_folder, file, file + '.json')
                    new_name = f'OsmQuery_{k}'
                    new_file = join(preset_folder, new_name, new_name + '.json')
                    rename(former_file, new_file)

                    files = os.listdir(join(preset_folder, file))
                    files_qml = filter(lambda file_ext: file_ext[-4:] == '.qml', files)
                    for file_qml in files_qml:
                        end_file_name = file_qml[len(file):]
                        new_file_qml = join(join(preset_folder, new_name), new_name + end_file_name)
                        old_file_qml = join(join(preset_folder, file), file + 'qml')
                        rename(old_file_qml, new_file_qml)
                    index = k

            if index:
                os.rmdir(join(preset_folder, f'OsmQuery_{index + 1}'))

    @staticmethod
    def add_empty_query_in_preset(data: dict) -> dict:
        """Add an empty query in a preset file"""
        data['query'].append('')
        data['query_layer_name'].append('')
        data['query_name'].append(tr('Query') + str(len(data['query'])))
        data['type_multi_request'].append([])
        data['keys'].append([])
        data['values'].append([])
        data['area'].append('')
        data['bbox'].append('')
        data['output_geom_type'].append(OSM_LAYERS)
        data['white_list_column'].append(WHITE_LIST)
        data['output_format'].append(None)
        data['output_directory'].append(None)

        return data

    def add_query_in_preset(self, existing_preset: str):
        """Add a query in a preset file"""
        preset_folder = query_preset()
        file_path = join(preset_folder, existing_preset, existing_preset + '.json')
        with open(file_path, encoding='utf8') as json_file:
            data = json.load(json_file, object_hook=as_enum)

        data['query'].append(self.query[0])
        data['query_layer_name'].append(self.name[0])
        data['query_name'].append(tr('Query') + str(len(data['query'])))
        data['type_multi_request'].append(self.type_multi_request[0])
        data['keys'].append(self.keys[0])
        data['values'].append(self.values[0])
        data['area'].append(self.area[0])
        data['bbox'].append(self.bbox[0])
        data['output_geom_type'].append(self.output_geom_type[0])
        data['white_list_column'].append(self.white_list[0])
        data['output_format'].append(self.output_format[0])
        data['output_directory'].append(self.output_directory[0])

        self.update_preset(data)

    @staticmethod
    def remove_query_in_preset(data: dict, num_query: int) -> dict:
        """Remove a query in a preset file."""
        data['query_layer_name'].pop(num_query)
        data['query_name'].pop(num_query)
        data['query'].pop(num_query)
        data['type_multi_request'].pop(num_query)
        data['keys'].pop(num_query)
        data['values'].pop(num_query)
        data['area'].pop(num_query)
        data['bbox'].pop(num_query)
        data['output_geom_type'].pop(num_query)
        data['white_list_column'].pop(num_query)
        data['output_format'].pop(num_query)
        data['output_directory'].pop(num_query)

        return data

    def rename_preset(self, former_name: str, new_name: str, data: dict):
        """Rename a preset query"""
        preset_folder = query_preset()
        old_folder = join(preset_folder, former_name)
        new_folder = join(preset_folder, new_name)
        os.mkdir(new_folder)

        new_file = join(new_folder, new_name + '.json')

        with open(new_file, 'w', encoding='utf8') as new_json_file:
            json.dump(data, new_json_file, cls=EnumEncoder)

        files = os.listdir(old_folder)
        files_qml = filter(lambda file_ext: file_ext[-4:] == '.qml', files)
        for file in files_qml:
            end_file_name = file[len(former_name):]
            new_file_qml = join(new_folder, new_name + end_file_name)
            old_file_qml = join(old_folder, file)
            rename(old_file_qml, new_file_qml)

        self.remove_preset(former_name)

    @staticmethod
    def update_preset(data: dict):
        """Rename a preset query"""
        preset_folder = query_preset()

        preset_file = join(preset_folder, data['file_name'], data['file_name'] + '.json')

        with open(preset_file, 'w', encoding='utf8') as json_file:
            json.dump(data, json_file, cls=EnumEncoder)
