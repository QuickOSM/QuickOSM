""" Parser of the presets file. """

import collections as col
import json
import logging
import os
import re
import xml.dom.minidom as xml

from QuickOSM.tools.i18n import setup_translation
from QuickOSM.tools.resources import resources_path


PRESET_PATH = resources_path('JOSM_preset', 'josm_preset.xml')
LOGGER = logging.getLogger('QuickOSM')


class PresetsParser:
    """Management of the presets file."""

    def __init__(self):

        self.file = xml.parse(PRESET_PATH)
        locale, translate_path = setup_translation(
            file_pattern="preset_{}.po")
        if translate_path:
            # LOGGER.info('Translation of presets to {}'.format(file_path))
            self.translate = self.preset_translate(translate_path)
        else:
            # LOGGER.info('Translation of presets not found: {}'.format(locale))
            self.translate = {}
        self.items = None

    def parser(self) -> col.namedtuple:
        """
        Parse the presets file

        :return: a dictionary of two dictionaries.
        Elements contains the data needed for the completer
        Items contains the data needed for the preset
        Items_combo contains couples key/value needed to specify more the query
        :rtype: namedTuple of two dictionaries
        """

        def fetch_keys(group, heirs_name: list) -> (list, bool):
            """
            This is a recursive function that dig into the file to find items inside groups

            Ancestors represents the path to the item/group
            Heirs contains all the items accessible from the item/group

            :group: an xml elements

            :return: the list of heirs.
            :rtype: (list, bool)
            """
            ancestors_name.append(group.getAttribute('name'))

            got_values = None

            children = filter(lambda child: self.node_filter(child), group.childNodes)
            for inner_group in children:
                heirs_item_name, got_values = fetch_keys(inner_group, [])

                if got_values:

                    if ancestors_name[0] in self.translate:
                        name_completion = self.translate[ancestors_name[0]]
                    else:
                        name_completion = ancestors_name[0]
                    if len(ancestors_name) != 1:
                        for ancestor in ancestors_name[1:]:
                            if ancestor in self.translate:
                                name_completion += '/' + self.translate[ancestor]
                            else:
                                name_completion += '/' + ancestor
                    ancestors_name.pop(-1)
                    icon = group.getAttribute('icon')
                    data_group = data('group', icon, ancestors_name, heirs_item_name)
                    elements[name_completion] = data_group
                else:
                    ancestors_name.pop(-1)
                heirs_name += heirs_item_name

            got_value_items = got_values if got_values else False

            children = filter(lambda child: self.node_filter(child, 'item'), group.childNodes)
            for item in children:
                data_item = {}
                name = item.getAttribute('name')

                got_value = False

                children = filter(lambda child: self.node_filter(child, 'key'), item.childNodes)
                for keys in children:
                    key = keys.getAttribute('key')
                    value = keys.getAttribute('value')

                    data_item[key] = value

                    if value:
                        got_value = True

                items[name] = data_item.copy()

                children = filter(lambda child: self.node_filter(child, 'combo'), item.childNodes)
                for combo in children:
                    key = combo.getAttribute('key')
                    value = combo.getAttribute('values').split(',')

                    data_item[key] = value

                items_combo[name] = data_item
                heirs_name.append(name)

                if got_value:

                    name_completion = ''
                    ancestors = []
                    for ancestor in ancestors_name:
                        if ancestor in self.translate:
                            name_completion += self.translate[ancestor] + '/'
                        else:
                            name_completion += ancestor + '/'
                        ancestors.append(ancestor)
                    if name in self.translate:
                        name_completion += self.translate[name]
                    else:
                        name_completion += name
                    icon = item.getAttribute('icon')
                    data_item = data('item', icon, ancestors, [name])
                    elements[name_completion] = data_item

                    got_value_items = True

            return heirs_name, got_value_items

        elements = {}
        items = {}
        items_combo = {}

        data = col.namedtuple('data', ['type', 'icon', 'ancestors', 'heirs'])

        root = self.file.firstChild
        children = filter(lambda child: self.node_filter(child), root.childNodes)

        for group in children:
            ancestors_name = []

            heirs_name, got_values = fetch_keys(group, [])

            if got_values:
                name = group.getAttribute('name')
                if name in self.translate:
                    name_completion = self.translate[name]
                else:
                    name_completion = name
                icon = group.getAttribute('icon')
                data_group = data('group', icon, ancestors_name[:-1], heirs_name)
                elements[name_completion] = data_group

        results = col.namedtuple('results', ['elements', 'items'])
        results = results(elements, items)

        self.items = items_combo

        return results

    @staticmethod
    def node_filter(node, search: str = 'group') -> bool:
        """
        Test if the node has the tag we search
        """
        if isinstance(node, xml.Element):
            return node.tagName == search

    def osm_keys_values(self) -> dict:
        """ Retrieval of key/value couple """
        couple = {}
        items = self.items.copy()

        old_couple_file = resources_path('json', 'map_features.json')
        with open(old_couple_file, encoding='utf8') as json_file:
            data = json.load(json_file)

        if not os.getenv('CI'):
            items['old_file'] = data

        key = []
        for item in items:
            for k in list(items[item].keys()):
                value = items[item][k]
                if k in key:
                    if isinstance(value, list):
                        for val in value:
                            if val not in couple[k]:
                                couple[k].append(val)
                    elif value not in couple[k]:
                        couple[k].append(value)
                elif isinstance(value, str):
                    key.append(k)
                    couple[k] = [value]
                elif isinstance(value, list):
                    key.append(k)
                    if value:
                        couple[k] = [value[0]]
                        for val in value[1:]:
                            couple[k].append(val)
                    else:
                        couple[k] = ['']

        return couple

    @staticmethod
    def preset_translate(file: str) -> dict:
        """Translate the preset in the language define in QGIS"""
        translate_dict = {}

        with open(file, encoding='utf8') as f:
            text = f.read()
            pattern = (
                "#: master_preset.xml:[0-9]+\\((group|item):name[a-zA-Z0-9|_ :\\/\\(\\)\\-\n\\&\\+#.]+"
                "(msgctxt \"[a-zA-Z_ \\-]+\"|)\nmsgid \"(.*?)\"\nmsgstr \"(.*?)\""
            )
            result = re.findall(pattern, text)

        for elem in result:
            translate_dict[elem[2]] = elem[3]

        return translate_dict
