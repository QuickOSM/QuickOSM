"""QuickOSM plugin init."""


# noinspection PyDocstring,PyPep8Naming
def classFactory(iface):
    """Launch of the plugin"""
    from QuickOSM.quick_osm import QuickOSMPlugin
    return QuickOSMPlugin(iface)
