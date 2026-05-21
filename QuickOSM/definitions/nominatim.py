"""List of Nominatim servers.

This file mustn't be modified by users. This file is updated with the plugin.

If you want to add some customs servers, add a file called 'custom_config.json'
in your profile_name/QuickOSM folder and add this template in it:

{
    "nominatim_servers": [
        "http://your_custom_url.com/search?"
    ]
}

QuickOSM will add your custom list to the list below.

A pull request is more than welcome if you want to add your server in QuickOSM
core by updating this list below.
"""


# The order is important. The first server will be the default.
NOMINATIM_SERVERS = [
    'https://nominatim.qgis.org/search?',
    'https://nominatim.openstreetmap.org/search?'
]
