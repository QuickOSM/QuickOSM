"""List of Overpass servers.

This file mustn't be modified by users. This file is updated with the plugin.

If you want to add some customs servers, add a file called 'custom_config.json'
in your profile_name/QuickOSM folder and add this template in it:

{
    "overpass_servers": [
        "http://your_custom_url.com/api/"
    ]
}

QuickOSM will add your custom list to the list below.

A pull request is more than welcome if you want to add your server in QuickOSM
core by updating this list below.
"""

# The list is from the OSM wiki page
# https://wiki.openstreetmap.org/wiki/Overpass_API
# Updated 2023-03-29
# Updated 2019-07-30
# The order is important. The first server will be the default one.
OVERPASS_SERVERS = [
    'https://overpass-api.de/api/',
    'https://overpass.kumi.systems/api/',
    'https://maps.mail.ru/osm/tools/overpass/api/',
    'https://overpass.openstreetmap.ru/api/',
    'https://overpass.osm.ch/api/',
    # Seems offline 2023-03-29 ?
    # 'https://overpass.nchc.org.tw/api/',
    # 'https://overpass.openstreetmap.fr/api/',
    # 'https://overpass-api.openhistoricalmap.org/api/'
]
