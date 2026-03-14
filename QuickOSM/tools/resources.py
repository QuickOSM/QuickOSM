"""Tools to work with resource files."""

import configparser
import shutil
import tempfile

from os.path import abspath, join, pardir, dirname

from qgis.PyQt import uic


def plugin_path(*args):
    """Get the path to plugin root folder.

    :param args List of path elements e.g. ['img', 'logos', 'image.png']
    :type args: str

    :return: Absolute path to the plugin path.
    :rtype: str
    """
    path = dirname(__file__)
    path = abspath(abspath(join(path, pardir)))
    for item in args:
        path = abspath(join(path, item))

    return path


def plugin_name():
    """Return the plugin name according to metadata.txt.

    :return: The plugin name.
    :rtype: basestring
    """
    metadata = metadata_config()
    name = metadata["general"]["name"]
    return name


def metadata_config() -> configparser:
    """Get the INI config parser for the metadata file.

    :return: The config parser object.
    :rtype: ConfigParser
    """
    path = plugin_path("metadata.txt")
    config = configparser.ConfigParser()
    config.read(path, encoding='utf8')
    return config


def plugin_test_data_path(*args, copy=False):
    """Get the path to the plugin test data path.

    :param args List of path elements e.g. ['img', 'logos', 'image.png']
    :type args: str

    :param copy: If the file must be copied into a temporary directory first.
    :type copy: bool

    :return: Absolute path to the resources folder.
    :rtype: str
    """
    path = abspath(abspath(join(plugin_path(), "test", "data")))
    for item in args:
        path = abspath(join(path, item))

    if copy:
        temp = tempfile.mkdtemp()
        shutil.copy(path, temp)
        return join(temp, args[-1])
    else:
        return path


def resources_path(*args):
    """Get the path to our resources folder.

    :param args List of path elements e.g. ['img', 'logos', 'image.png']
    :type args: str

    :return: Absolute path to the resources folder.
    :rtype: str
    """
    path = abspath(abspath(join(plugin_path(), "resources")))
    for item in args:
        path = abspath(join(path, item))

    return path


def load_ui(*args):
    """Get compile UI file.

    :param args List of path elements e.g. ['img', 'logos', 'image.png']
    :type args: str

    :return: Compiled UI file.
    """
    ui_class, _ = uic.loadUiType(resources_path("ui", *args))
    return ui_class
