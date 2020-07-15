#!/usr/bin/env python

"""
Transport System Analysis -- Copyright (C) 2020, Alexander Tsyba
Comes under GNU GPL v3

dump.py is the first step in transport system analysis - downloading routes and
stations of specified cities into SQLite database. This is a needed evil as
it is much easier to work with info from local DB vs. referring to API
anytime for different actions like building graphs and analysing shortest paths.

Cities are taken from cities.txt (or cities_man.txt, if you want to enter them
manually) in the format [city, country] in English;

In case you get a Nominatim error, OSM does not recognize the city in the way
you've written it;

If your Internet connection was interruped, you can rerun the script - data
should be maintained in DB and Pycache and continue downloading from the
place you've stopped;

Next step after dump.py is graphs.py to build non-connected graph object first.
"""

import re
import sqlite3

from OSMPythonTools.overpass import overpassQueryBuilder, Overpass
from OSMPythonTools.nominatim import Nominatim

import model_parameters


def add_system(network_name, cursor):
    # function updates the list of transport systems in database and returns id
    # of created system
    cursor.execute('INSERT OR IGNORE INTO RailwaySystem (name) VALUES (?)',
                   (network_name.rstrip(),))
    cursor.execute('SELECT id FROM RailwaySystem WHERE name = ? LIMIT 1',
                   (network_name.rstrip(),))
    return cursor.fetchone()[0]


def add_route(route, system_id, cursor):
    # function adds route (refer to
    cursor.execute('SELECT id FROM Route WHERE id = ?', (route.id(),))
    if not database.fetchall():
        # checks if the route is route already in database
        if route.tag('ref') is None:
            # if route number (ref attribute in OSM) is not specified, ask user
            # to provide it manually by looking up relation id in OSM
            print('Route id ' + str(route.id()) + ' has no *ref* attribute.'
                                                  'Please kind provide it '
                                                  'manually: ')
            route_ref = input()
        else:
            route_ref = route.tag('ref')  # else use one from OSM
        cursor.execute('''INSERT INTO Route (id, ref, system_id, type)
                        VALUES (?, ?, ?, ?)''',
                       (route.id(), route_ref, system_id, route.tag('route')))
        return route.id()
        # insert route id, number (ref), relation to system id and route type
        # (transport type) in DB
    else:
        # if route is in the system, return False for less detailed OSM route
        # types not to add duplicated routes as one route is enough given route
        # representation in OSM ways and nodes ('virtual' stops)
        if route.tag('route') == 'tram' or route.tag('route') == 'bus' or\
                route.tag('route') == 'trolleybus':
            return False
        else:
            # for more high-quality data heavy rail transit, add even duplicated
            # routes to ensure data sufficiency when iterating over stations in
            # routes
            return route.id()


def add_way(way, route_id, cursor):
    # identical to add_route, but adds a way - 1-st level child component of
    # route in OSM, used for less detailed OSM route types where we cannot
    # guarantee correctness of real stops and connections between them, so we
    # have to iterate over ways instead of stations
    cursor.execute('SELECT id FROM Way WHERE id = ? LIMIT 1', (way.id(),))
    result = database.fetchone()
    if not result:
        cursor.execute('INSERT INTO Way (id, route_id) VALUES (?, ?)',
                       (way.id(), route_id))
        return way.id()
    else:
        return False
        # not adding duplicating ways for same reasons as routes for lower
        # quality data OSM transport


def add_node(node, route_id, cursor, bbox, way_id, order):
    # function to add OSM nodes as 'virtual' stops for lower quality and
    # importance means of transit
    cursor.execute('SELECT id FROM Station WHERE id = ?', (node.id(),))
    result = database.fetchone()
    if not result:  # adding node only if it not yet in DB
        bbox_lat = bbox[0]
        bbox_lon = bbox[1]
        if bbox_lat[0] <= round(node.lat(), model_parameters.GEO_PRECISION)\
                <= bbox_lat[1] and \
                bbox_lon[0] <= round(node.lon(),
                                     model_parameters.GEO_PRECISION)\
                <= bbox_lon[1]:
            # since some bus routes may go far beyond aglomerration yet serving
            # city mainly, we take bounding box of city area in OSM
            # and add only stops within this bounding box by checking if
            # lat / lon of node falls within bbox
            cursor.execute('''INSERT INTO 
                Station (name, longitude, latitude, route_id, way_id, way_order)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (node.id(),
                      round(node.lon(), model_parameters.GEO_PRECISION),
                      round(node.lat(), model_parameters.GEO_PRECISION),
                      route_id, way_id, order))
            # order parameter is used to indicate node order in the way in order
            # to correctly reconstruct way in the graph later
        return True
    else:
        return False


def add_station(station, route_id, cursor):
    # for heavy rail transit we add real stations
    station_enumeration = re.search('\d+$', str(station.tag('name')))

    # some stations may later cause mess if they are cross-platform and named in
    # the same way but with number in the end. For example, St. Petersburg has
    # cross-platform interchange Teknologichesky Institue 1 -
    # Teknologichesky Institue 2 due to x-platform interchange, both subway
    # lines end up having both stations at almost same lat / lon in OSM in
    # different routes - back and forth. Since we want data sufficiency for
    # heavy rail transit and add both one and back way routes the only
    # solution is to cut number in the end by regular expression and ensure that
    # interchange stations have same name
    # # #
    # !!! PROBLEM can still appear if there will be x-platform with completely
    # different names. But usally x-platforms named in same manner and differ by
    # indexes

    if station_enumeration is not None:
        unenumerated_station_name = str(
            station.tag('name')
        ).rstrip(station_enumeration.group(0)).rstrip()
    else:
        unenumerated_station_name = str(station.tag('name'))
    cursor.execute('SELECT id FROM Station WHERE name = ? AND route_id = ?',
                   (unenumerated_station_name, route_id))
    if not database.fetchall():
        # rest of the function just checks if station not in the base yet and
        # inserts it
        cursor.execute('''INSERT INTO 
            Station (name, longitude, latitude, route_id)
            VALUES (?, ?, ?, ?)
            ''', (unenumerated_station_name,
                  round(station.lon(), model_parameters.GEO_PRECISION),
                  round(station.lat(), model_parameters.GEO_PRECISION),
                  route_id))
    return True


def osm_query(area, route_types):
    # function to build OSM query object for area and transport type and return
    # back query and transport type used
    query = overpassQueryBuilder(
        area=area,
        elementType=['relation'],
        selector=['"route"="' + route_types + '"'],
        out='body'
    )
    return query, route_types


def query_to_base(city, bbox, system_id, db_connection, cursor, query):
    # function to execute OSM query and write results to DB
    result = osmAPI.query(query[0])  # contacting OSM based on defined query
    if not result.elements():
        print('No ' + query[1] + ' in ' + city)
        return False
        # in case transport type is not present in the city, exit function
    print('Adding ' + city.rstrip() + ' ' + query[1] + ' in the base...')

    # below are slightly different functions depending on the type of transport
    # due to the differencies in OSM data quality
    # # #
    # for 'train' (city trains), 'subway' and 'light_rail' - data is more or
    # less good and having real stations is important due to high capacity and
    # frequency, so we will construct graph on real stations (stops)
    # It is important to operate with real stations for heavy
    # rail transit, as usually average haul between stations is longer than
    # acceptable pedestrian walk and you cannot assume that person can get on
    # the route at any point and interchange to cross-route in any point (
    # interchange may not be built).
    # # #
    # for 'bus', 'trolleybus' and 'tram' data on stops is often incomplete, so
    # we will build graph on each 20-th node from route ways (20 is chosen as
    # empirical balance between graph complexity and distance between nodes - to
    # reflect real distance between stops)
    # approach above is also justified that usually neighbouring bus / tram
    # stops are accessible by feet, so having precision in stop place is not
    # that critical

    if query[1] == 'train':
        # since OSM tags 'train' for all trains (long haul and city), we have to
        # ask user which routes are really city trains
        # not to make user wait for next route while previous is being added, we
        # will collect all routes first and add only selected ones at 2nd step
        routes_to_add = list()
        for route in result.elements():
            if route.tag('name') is not None:
                route_name = route.tag('name')
            elif route.tag('description') is not None:
                route_name = route.tag('description')  # sometimes route name is
                # mistakenly stored in 'description' tag
            else:
                route_name = str(route.id()) + ' ' + str(route.tag('ref'))
                # 'ref' OSM tag usually stores route number
            print('Add route (' + str(route.id()) + ') -- ' + str(route_name) +
                  '? (Y/N): ', end="")
            decision = input()
            if decision.upper() == 'Y':
                routes_to_add.append(route)
        for route in routes_to_add:
            route_id = add_route(route, system_id, cursor)  # firstly we add the
            # route itself to base
            stations = list()
            # since route members are ways and nodes in OSM, we iterate
            # through them and select only nodes as stations
            for station in route.members(shallow=False):
                # shallow=False downloads all metadata for members immediately,
                # so we can store the stations right here
                if station.type() == 'node':
                    stations.append(station)
            if not stations:
                continue
            # if we see that last and first station are the same, then route is
            # circular and we reflect this in database to properly build a graph
            if stations[0].id() == stations[-1].id():
                cursor.execute('UPDATE Route SET circle = ? WHERE id = ?',
                               (1, route_id))
            for station in stations:
                # once we got all the stations we add them to database
                add_station(station, route_id, cursor)
            db_connection.commit()
        db_connection.commit()
        print('done!')
        return True
    elif query[1] == 'subway' or query[1] == 'light_rail':
        # for subway and light_rail script is identical to train, but we add
        # everything without user prompt since subway / light rail rarely go
        # outside city boundaries
        for route in result.elements():
            stations = list()
            for station in route.members(shallow=False):
                if station.type() == 'node':
                    stations.append(station)
            if not stations or len(stations) == 1:
                continue
            route_id = add_route(route, system_id, cursor)
            if stations[0].id() == stations[-1].id():
                cursor.execute('UPDATE Route SET circle = ? WHERE id = ?',
                               (1, route_id))
            for station in stations:
                add_station(station, route_id, cursor)
            db_connection.commit()
        db_connection.commit()
        print('done!')
        return True
    elif query[1] == 'tram' or query[1] == 'trolleybus':
        # for tram and trolleybus, due to low data quality in OSM, we process
        # all individual 'ways' of those routes and add every n-th node of
        # each way + 1st and last node. n is global parameter; recommended
        # value is 20
        for route in result.elements():
            # for each route we search for ways without OSM 'role' to exclude
            # boundaries of platforms / stops which are also ways and also
            # can belong to route and only include actual route parts
            ways = list()
            for way in route.members(shallow=False):
                if way.type() == 'way' and way.tag('role') is None:
                    ways.append(way)
            if not ways:
                continue  # ignoring empty routes with no ways
            route_id = add_route(route, system_id, cursor)
            # adding route itself, if it is already in the base, skipping to
            # next one
            if not route_id:
                continue
            for way in ways:
                # for each way in the route we add it to database itself and
                # set two counters, in order to track node order and easily
                # sort them to correctly build the graph, and i counter is
                # used to add only each n-th node
                order = 1
                i = 0
                way_id = add_way(way, route_id, cursor)
                if way_id:
                    if way.nodes()[0].id() == way.nodes()[-1].id():
                        # this tweak is used to correctly process
                        # roundabouts. We must add all nodes if way is
                        # roundabouts, since we never know in advance for
                        # further routes, which roundabouts nodes will be as
                        # well used to connect with adjacent way nodes - it
                        # differs route by route especially with complex
                        # roundabouts with lots of exits
                        for node in way.nodes():
                            add_node(node, route_id, cursor, bbox, way_id,
                                     order)
                            # while adding nodes, we also pass OSM area (
                            # city) bounding box as a parameter, to ensure
                            # that we are adding only parts of routes within
                            # the cities. Since bbox is squared, it captures
                            # slightly more than official administrative
                            # boundaries, which empirically prove to
                            # represent actual agglomeration
                            order += 1
                    else:
                        # for usual ways, we add 1st, last and n-th node
                        for node in way.nodes():
                            i += 1
                            if i == 1 or i == len(way.nodes()) or i % \
                                    model_parameters.NODE_PRECISION == 0:
                                add_node(node, route_id, cursor, bbox, way_id,
                                         order)
                                order += 1
                    db_connection.commit()  # flush to SQlite after each way
                else:
                    # if way is already in a base, we just add 1st and last
                    # node as an insurance - in case data connection was
                    # interrupted during way nodes download (and I have wrote
                    # no system to track interruption point)
                    add_node(way.nodes()[0], route_id, cursor, bbox, way_id, 1)
                    add_node(way.nodes()[-1], route_id, cursor, bbox, way_id, 2)
                    db_connection.commit()
            if ways[0].nodes()[0].id() == ways[-1].nodes()[-1].id():
                # if first and last node of route is the same, we mark it as
                # circle to properly bulid the graph
                cursor.execute('UPDATE Route SET circle = ? WHERE id = ?',
                               (1, route_id))
            db_connection.commit()
        db_connection.commit()
        print('done!')
        return True
    else:
        # in case transport type is the bus, code is identical to trams and
        # trolleybus, but before adding any routes, we iterate through them
        # and ask user to confirm whether route should be added or not - OSM
        # marks inter city buses and inner city buses in a same way. There is
        # still a foolproof check on nodes within city bounding box,
        # but downloading all nodes from intercity buses and checking for
        # bbox would take eternity
        routes_to_add = list()
        for route in result.elements():
            if route.tag('name') is not None:
                route_name = route.tag('name')
            elif route.tag('description') is not None:
                route_name = route.tag('description')
            else:
                route_name = str(route.id()) + ' ' + str(route.tag('ref'))
            print('Add route (' + str(route.id()) + ') -- ' + str(route_name) +
                  '? (Y/N): ', end="")
            decision = input()
            if decision.upper() == 'Y':
                routes_to_add.append(route)
        for route in routes_to_add:
            ways = list()
            for way in route.members(shallow=False):
                if way.type() == 'way' and way.tag('role') is None:
                    ways.append(way)
            if not ways:
                continue
            route_id = add_route(route, system_id, cursor)
            if not route_id:
                continue
            for way in ways:
                order = 1
                i = 0
                way_id = add_way(way, route_id, cursor)
                if way_id:
                    if way.nodes()[0].id() == way.nodes()[-1].id():
                        for node in way.nodes():
                            add_node(node, route_id, cursor, bbox, way_id,
                                     order)
                            order += 1
                    else:
                        for node in way.nodes():
                            i += 1
                            if i == 1 or i == len(way.nodes()) or i %\
                                    model_parameters.NODE_PRECISION == 0:
                                add_node(node, route_id, cursor, bbox, way_id,
                                         order)
                                order += 1
                    db_connection.commit()
                else:
                    add_node(way.nodes()[0], route_id, cursor, bbox, way_id, 1)
                    add_node(way.nodes()[-1], route_id, cursor, bbox, way_id, 2)
                    db_connection.commit()
            if ways[0].nodes()[0].id() == ways[-1].nodes()[-1].id():
                cursor.execute('UPDATE Route SET circle = ? WHERE id = ?',
                               (1, route_id))
            db_connection.commit()
        db_connection.commit()
        print('done!')
        return True


# main module starts here with DB connection and DB scheme creation
db_connection = sqlite3.connect('systems.sqlite')
database = db_connection.cursor()

database.executescript('''
    CREATE TABLE IF NOT EXISTS Station (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        name TEXT,
        longitude REAL,
        latitude REAL,
        route_id INTEGER,
        open_year YEAR,
        ridership INTEGER,
        way_id INTEGER,
        way_order TINYINT
    );
    
    CREATE TABLE IF NOT EXISTS Route (
        id INTEGER NOT NULL PRIMARY KEY UNIQUE,
        ref TEXT,
        system_id INTEGER,
        circle TINYINT,
        type TEXT
    );
        
    CREATE TABLE IF NOT EXISTS RailwaySystem (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        name TEXT UNIQUE,
        stations_number SMALLINT,
        avg_haul INTEGER,
        optimality_indx REAL
    );
    
    CREATE TABLE IF NOT EXISTS Way (
        id INTEGER NOT NULL PRIMARY KEY UNIQUE,
        route_id INTEGER
    );
''')

# creating Nominatim and OSM api objects
nominatim = Nominatim()  # API to retreat OSM area id from human name of city
osmAPI = Overpass()

with open('cities_man.txt', 'r', encoding='utf8') as cities_list:
    for city in cities_list.readlines():
        # we are trying to download data for each city in generated / manual
        # file with cities list
        try:  # trying to catch Nominatim exception - wrong city name
            nominatim_query = nominatim.query(city)
            area = nominatim_query.areaId()  # getting area id of city
            # nominatim returns JSON with main area parameters, including
            # squared bounding box limited by most outstanding area points
            bbox_raw = nominatim_query.toJSON()[0]['boundingbox']
            bbox_lat = sorted(list(map(
                lambda x: round(x, model_parameters.GEO_PRECISION),
                map(float, bbox_raw)
            ))[:2])
            bbox_lon = sorted(list(map(
                lambda x: round(x, model_parameters.GEO_PRECISION),
                map(float, bbox_raw)
            ))[2:])
            bbox = (bbox_lat, bbox_lon)  # parsing bbox coordinates from JSON
            # and rounding to 5 (precision of few meters)
            # Next steps - building queries for all transport types
            query_subway = osm_query(area, 'subway')
            query_train = osm_query(area, 'train')
            query_lrt = osm_query(area, 'light_rail')
            query_tram = osm_query(area, 'tram')
            query_bus = osm_query(area, 'bus')
            query_trolleybus = osm_query(area, 'trolleybus')
        except Exception:  # nominatim returns just general exception
            print('No such city as ' + city.rstrip() + '!')
            continue
        # if everything was ok and iteration was not skipped in the
        # exception, we add new transport system in the base and download all
        # the data for each transport type in the DB
        system_id = add_system(city, database)
        query_to_base(city, bbox, system_id, db_connection, database,
                      query_subway)
        query_to_base(city, bbox, system_id, db_connection, database,
                      query_train)
        query_to_base(city, bbox, system_id, db_connection, database,
                      query_lrt)
        query_to_base(city, bbox, system_id, db_connection, database,
                      query_tram)
        query_to_base(city, bbox, system_id, db_connection, database,
                      query_bus)
        query_to_base(city, bbox, system_id, db_connection, database,
                      query_trolleybus)

print("All cities added!")
db_connection.close()

# error handling - correctly
# spread-index
# betweness cenrality?
# vs. car path optimality - build route via Google API?
# рельсовый транспорт логично смотреть потому что это анализ того, как власти направили потоки!

# анализ начать с метро, гор поездов и ЛРТ...
# изложить в статье цели и след шаги - GUI, плотность населения и AI
# обосновать почему это а не гугл например
# сразу сделать дисклеймер про качество кода
