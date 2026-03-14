"""Tools about version."""

from QuickOSM.tools.resources import metadata_config


def format_version_integer(version_string: str):
    """Transform version string to integers to allow comparing versions.

    Transform "0.1.2" into "000102"
    Transform "10.9.12" into "100912"
    """
    return int("".join([a.zfill(2) for a in version_string.strip().split(".")]))


def version(remove_v_prefix=True) -> str:
    """Return the version defined in metadata.txt."""
    v = metadata_config()["general"]["version"]
    if v.startswith("v") and remove_v_prefix:
        v = v[1:]
    return v
