from math import acos, sin, cos, radians


def geo_distance(long_from, lat_from, long_to, lat_to):
    if long_from == long_to and lat_from == lat_to:
        return 0
    earth_radius = 6371
    return earth_radius * acos(
        sin(radians(lat_from)) * sin(radians(lat_to)) +
        cos(radians(lat_from)) * cos(radians(lat_to)) *
        cos(radians(long_to) - radians(long_from))
    )
