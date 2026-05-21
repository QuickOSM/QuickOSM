"""Tests for the parser of the presets."""

import collections as col
import unittest
import xml.dom.minidom as xml

from QuickOSM.core.parser.preset_parser import PresetsParser


class TestPresetParser(unittest.TestCase):
    """Tests for the parser of the presets."""

    def setUp(self):
        self.maxDiff = None
        self.parser = PresetsParser()
        self.data = col.namedtuple('data', ['type', 'icon', 'ancestors', 'heirs'])

    def test_parser_simple_files(self):
        """ Test if the parser return the format expected"""

        # Simple file 1 group 1 item
        xml_template = (
            '<presets>'
            '<group name="Highways">'
            '<item name="route">'
            '<key key="foo" value="bar"/>'
            '</item>'
            '</group>'
            '</presets>'
        )
        expected_dict_item = {'route': {'foo': 'bar'}}
        expected_dict_element = {
            'Highways/route': self.data(
                type='item', icon='',
                ancestors=['Highways'], heirs=['route']
            ),
            'Highways': self.data(
                type='group', icon='',
                ancestors=[], heirs=['route']
            )
        }
        self.parser.file = xml.parseString(xml_template)
        result = self.parser.parser()
        self.assertEqual(expected_dict_item, result.items)
        self.assertEqual(expected_dict_element, result.elements)

        # Simple file 1 group 2 items
        xml_template = (
            '<presets>'
            '<group name="Highways">'
            '<item name="route">'
            '<key key="foo" value="bar"/>'
            '</item>'
            '<item name="railway">'
            '<key key="bar" value="foo"/>'
            '</item>'
            '</group>'
            '</presets>'
        )
        expected_dict_item = {
            'route': {'foo': 'bar'},
            'railway': {'bar': 'foo'}
        }
        expected_dict_element = {
            'Highways/route': self.data(
                type='item', icon='',
                ancestors=['Highways'], heirs=['route']
            ),
            'Highways/railway': self.data(
                type='item', icon='',
                ancestors=['Highways'], heirs=['railway']
            ),
            'Highways': self.data(
                type='group', icon='',
                ancestors=[], heirs=['route', 'railway']
            )
        }
        self.parser.file = xml.parseString(xml_template)
        result = self.parser.parser()
        self.assertEqual(expected_dict_item, result.items)
        self.assertEqual(expected_dict_element, result.elements)

    def test_parser_complex_files(self):
        """ Test if the parser return the format expected"""

        # Complex file 3 groups, 2 groups interlocked, multiple items
        xml_template = (
            '<presets>'
            '<group name="country">'
            '<group name="Highways">'
            '<item name="route">'
            '<key key="foo" value="bar"/>'
            '</item>'
            '<item name="railway">'
            '<key key="bar" value="foo"/>'
            '</item>'
            '</group>'
            '<group name="Road">'
            '<item name="tramway">'
            '<key key="foobar" value="barfoo"/>'
            '</item>'
            '</group>'
            '</group>'
            '</presets>'
        )
        expected_dict_item = {
            'route': {'foo': 'bar'},
            'railway': {'bar': 'foo'},
            'tramway': {'foobar': 'barfoo'}
        }
        expected_dict_element = {
            'country/Highways/route': self.data(
                type='item', icon='', ancestors=['country', 'Highways'], heirs=['route']
            ),
            'country/Highways/railway': self.data(
                type='item', icon='', ancestors=['country', 'Highways'], heirs=['railway']
            ),
            'country/Highways': self.data(
                type='group', icon='', ancestors=['country'], heirs=['route', 'railway']
            ),
            'country/Road/tramway': self.data(
                type='item', icon='', ancestors=['country', 'Road'], heirs=['tramway']
            ),
            'country/Road': self.data(
                type='group', icon='', ancestors=['country'], heirs=['tramway']
            ),
            'country': self.data(
                type='group', icon='', ancestors=[], heirs=['route', 'railway', 'tramway']
            )
        }
        self.parser.file = xml.parseString(xml_template)
        result = self.parser.parser()
        self.assertEqual(expected_dict_item, result.items)
        self.assertEqual(expected_dict_element, result.elements)

        # Complex file groups interlocked, multiple items 'a,d' keys
        xml_template = (
            '<presets>'
            '<group name="country">'
            '<group name="Highways">'
            '<item name="route">'
            '<key key="foo" value="bar"/>'
            '<key key="foofoo" value="barbar"/>'
            '</item>'
            '<item name="railway">'
            '<key key="bar" value="foo"/>'
            '</item>'
            '</group>'
            '<group name="Road">'
            '<item name="tramway">'
            '<key key="foobar" value="barfoo"/>'
            '</item>'
            '</group>'
            '</group>'
            '<group name="River">'
            '<item name="boat">'
            '<key key="barfoo" value="foobar"/>'
            '</item>'
            '</group>'
            '</presets>'
        )
        expected_dict_item = {
            'route': {'foo': 'bar', 'foofoo': 'barbar'},
            'railway': {'bar': 'foo'},
            'tramway': {'foobar': 'barfoo'},
            'boat': {'barfoo': 'foobar'}
        }
        expected_dict_element = {
            'country/Highways/route': self.data(
                type='item', icon='', ancestors=['country', 'Highways'], heirs=['route']
            ),
            'country/Highways/railway': self.data(
                type='item', icon='', ancestors=['country', 'Highways'], heirs=['railway']
            ),
            'country/Highways': self.data(
                type='group', icon='', ancestors=['country'], heirs=['route', 'railway']
            ),
            'country/Road/tramway': self.data(
                type='item', icon='', ancestors=['country', 'Road'], heirs=['tramway']
            ),
            'country/Road': self.data(
                type='group', icon='', ancestors=['country'], heirs=['tramway']
            ),
            'country': self.data(
                type='group', icon='', ancestors=[], heirs=['route', 'railway', 'tramway']
            ),
            'River/boat': self.data(
                type='item', icon='', ancestors=['River'], heirs=['boat']
            ),
            'River': self.data(
                type='group', icon='', ancestors=[], heirs=['boat']
            )
        }
        self.parser.file = xml.parseString(xml_template)
        result = self.parser.parser()
        self.assertEqual(expected_dict_item, result.items)
        self.assertEqual(expected_dict_element, result.elements)

    def test_retrieval_couples(self):
        """ Test if we can retrieve the key/value couples """

        xml_template = (
            '<presets>'
            '<group name="country">'
            '<group name="Highways">'
            '<item name="route">'
            '<key key="foo" value="bar"/>'
            '</item>'
            '<item name="railway">'
            '<key key="foo" value="barbar"/>'
            '<key key="bar" value="foo"/>'
            '</item>'
            '</group>'
            '<group name="Road">'
            '<item name="tramway">'
            '<key key="foobar" value="barfoo"/>'
            '<key key="bar" value="foo"/>'
            '</item>'
            '</group>'
            '</group>'
            '</presets>'
        )
        expected_couples = {
            'foo': ['bar', 'barbar'],
            'bar': ['foo'],
            'foobar': ['barfoo'],
        }

        self.parser.file = xml.parseString(xml_template)
        self.parser.parser()
        couples = self.parser.osm_keys_values()
        self.assertEqual(expected_couples, couples)

        xml_template = (
            '<presets>'
            '<group name="country">'
            '<group name="Highways">'
            '<item name="route">'
            '<key key="foo" value="bar"/>'
            '<key key="bar" value="foo"/>'
            '</item>'
            '<item name="railway">'
            '<key key="bar" value="foo"/>'
            '</item>'
            '</group>'
            '<group name="Road">'
            '<item name="tramway">'
            '<key key="bar" value="foofoo"/>'
            '<key key="foobar" value="barfoo"/>'
            '<combo key="barfoo" values="foobar,foobarfoo,barfoobar"/>'
            '</item>'
            '</group>'
            '</group>'
            '</presets>'
        )
        expected_couples = {
            'foo': ['bar'],
            'bar': ['foo', 'foofoo'],
            'foobar': ['barfoo'],
            'barfoo': ['foobar', 'foobarfoo', 'barfoobar'],
        }

        self.parser.file = xml.parseString(xml_template)
        self.parser.parser()
        couples = self.parser.osm_keys_values()
        self.assertEqual(expected_couples, couples)


if __name__ == '__main__':
    unittest.main()
