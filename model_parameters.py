#!/usr/bin/env python

"""
Transport System Analysis -- Copyright (C) 2020, Alexander Tsyba
Comes under GNU GPL v3

model_parameters.py stores list of parameters to run the model with.
Constants are organized by respective project modules

"""

# GENERAL - used within (almost) all modules
GEO_PRECISION = 5  # rounding base for longtitude / latitude. 5 is enough for
# performance / precision balance (few meters)

# DUMP.PY - downloading OSM data to base
NODE_PRECISION = 20  # for bus, tram, etc. we download each OSM node,
# not just stop. node_precision tells N in N-th node to download. 20 is more
# or less represents real distance between the stops (100-1500 meters).

# GRAPHS.PY - building raw unconnected graphs
EDGE_COEF = {
            'subway': 1,
            'train': 1.125,
            'light_rail': 0.75,
            'tram': 0.5,
            'bus': 0.375,
            'trolleybus': 0.375
}
EDGE_COLOR = {
            'subway': 'black',
            'train': 'blue',
            'light_rail': 'cyan',
            'tram': 'magenta',
            'bus': 'red',
            'trolleybus': 'red'
}
