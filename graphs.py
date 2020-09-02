#!/usr/bin/env python

"""
Transport System Analysis -- Copyright (C) 2020, Alexander Tsyba
Comes under GNU GPL v3

graphs.py is the second step in transport system analysis - building
non-connected graphs out of the info stored in SQLite database. Graphs are
non-connected in a sense that interchange edges between different routes /
means of transport are not added at this stage.

Graphs are built one by one following list of cities from DB and stored in
'raw' directory as Python NetworkX graph objects. If graph was already built,
script ignores that city.

Also script attempts to fix 'weird' egdes that may pop up due to low data
quality and cleans up database, leaving only nodes that were added to the graph.

After successful execution of this script, you are HIGHLY recommended to
check visualisation of 'raw' result with draw_graph.py before proceeding to
interchanges_to_graph.py, that will add interchanges between routes and means of
transport to graph.
"""
import os.path
import networkx as nx
import sqlite3
from statistics import median

from get_distance import geo_distance # function that calculates distance
# using coordinates
import model_parameters


def routes_to_graph(graph, system_id, routes_type, database):
    # this function adds to graph heavy rail systems for which data quality is
    # good in OSM (rare cases of missing stations on routes) and which by
    # design doesn't deviate a lot from straight line between stations A and
    # B, so we can simply add all stations with coordinates and connect them
    # with direct edges, merging duplicating stations in progress and
    # resulting with 'subway map' quality of graph (no duplicating stations /
    # edges). Important assertion for this technique is that NO station is
    # missed in OSM on route relation representing 'one-way' and relation of
    # 'back-way' (in OSM you have separate routes from A to B and B to A as
    # relations). See more details of this logic in dump.py comments.
    database.execute('''SELECT id, ref, circle FROM Route 
                        WHERE system_id = ? AND type = ?''',
                     (system_id, routes_type))
    for route in database.fetchall():
        previous_station = list()
        print('Working on route ' + str(route[1]) + ', id=' + str(route[0]) +
              '...')
        database.execute('''SELECT id, name, longitude, latitude, route_id
                            FROM Station WHERE route_id = ? ORDER BY id''',
                         (route[0],))
        route_stations = database.fetchall()
        index = -1
        for station in route_stations:
            index += 1
            station_already_exists_id = 0
            station_already_exists_id_route_id = 0
            database.execute('''SELECT Station.id, Route.id
                                FROM Station JOIN Route JOIN RailwaySystem 
                                ON Station.route_id = Route.id
                                AND Route.system_id = RailwaySystem.id 
                                WHERE Station.name = ? AND Station.id <> ?
                                AND Route.ref = ? AND RailwaySystem.id = ?
                                ORDER BY Station.id''',
                             (station[1], station[0], route[1], system_id))
            existing_stations = database.fetchall()
            for existing_station in existing_stations:
                if graph.has_node(existing_station[0]):
                    station_already_exists_id = existing_station[0]
                    station_already_exists_id_route_id = existing_station[1]
                    break
            if station_already_exists_id == 0:
                database.execute('''SELECT Station.id, Route.id, Station.name 
                                    FROM Station JOIN Route
                                    ON Station.route_id = Route.id
                                    WHERE Station.name = ? 
                                    AND Station.longitude = ? 
                                    AND Station.latitude = ? 
                                    AND Route.ref <> ?
                                    ORDER BY Station.id''',
                                 (station[1], station[2], station[3], route[1]))
                existing_stations = database.fetchall()
                for existing_station in existing_stations:
                    exit_cycle = False
                    if graph.has_node(existing_station[0]):
                        station_already_exists_id = existing_station[0]
                        station_already_exists_id_route_id = existing_station[1]
                        break
                    database.execute('''SELECT Station.id, Route.id 
                                        FROM Station JOIN Route
                                        ON Station.route_id = Route.id
                                        WHERE Station.name = ? 
                                        AND Station.longitude <> ? 
                                        AND Station.latitude <> ? 
                                        AND Route.ref <> ?
                                        ORDER BY Station.id''',
                                     (station[1], station[2],
                                      station[3], route[1]))
                    for adjacent_existing_stations in database.fetchall():
                        exit_cycle_2 = False
                        if graph.has_node(adjacent_existing_stations[0]):
                            neighbours_of_existing_node = nx.all_neighbors(
                                graph,
                                adjacent_existing_stations[0]
                            )
                            for neighbour in neighbours_of_existing_node:
                                neighbour_name =\
                                    nx.get_node_attributes(graph,
                                                           'name')[neighbour]
                                if previous_station and\
                                        index + 1 < len(route_stations):
                                    if neighbour_name == previous_station[1] or\
                                            neighbour_name == \
                                            route_stations[index + 1][1]:
                                        station_already_exists_id =\
                                            adjacent_existing_stations[0]
                                        station_already_exists_id_route_id =\
                                            adjacent_existing_stations[1]
                                        exit_cycle = True
                                        exit_cycle_2 = True
                                        break
                                elif previous_station and\
                                        index + 1 >= len(route_stations):
                                    if neighbour_name == previous_station[1]:
                                        station_already_exists_id =\
                                            adjacent_existing_stations[0]
                                        station_already_exists_id_route_id =\
                                            adjacent_existing_stations[1]
                                        exit_cycle = True
                                        exit_cycle_2 = True
                                        break
                            if exit_cycle_2:
                                break
                    if exit_cycle:
                        break
            if station_already_exists_id != 0:
                if (not previous_station) or\
                        graph.has_edge(previous_station[0],
                                       station_already_exists_id):
                    database.execute('''SELECT id, name, longitude,
                                        latitude, route_id 
                                        FROM Station WHERE id = ? LIMIT 1''',
                                     (station_already_exists_id,))
                    previous_station = database.fetchone()
                    continue
                elif not graph.has_edge(previous_station[0],
                                        station_already_exists_id) and \
                        previous_station[4] ==\
                        station_already_exists_id_route_id:
                    database.execute('''SELECT id, name, longitude,
                                        latitude, route_id 
                                        FROM Station WHERE id = ? LIMIT 1''',
                                     (station_already_exists_id,))
                    previous_station = database.fetchone()
                    continue
                else:
                    distance = geo_distance(
                        previous_station[2],
                        previous_station[3],
                        nx.get_node_attributes(
                            graph,
                            'pos'
                        )[station_already_exists_id][0],
                        nx.get_node_attributes(
                            graph,
                            'pos'
                        )[station_already_exists_id][1]
                    )
                    graph.add_edge(previous_station[0],
                                   station_already_exists_id,
                                   weight=
                                   (distance /
                                   model_parameters.EDGE_COEF[routes_type]),
                                   color=
                                   model_parameters.EDGE_COLOR[routes_type],
                                   type=routes_type
                                   )
                    database.execute('''SELECT id, name, longitude,
                                        latitude, route_id
                                        FROM Station WHERE id = ? LIMIT 1''',
                                     (station_already_exists_id,))
                    previous_station = database.fetchone()
            else:
                graph.add_node(station[0], name=station[1],
                               pos=(station[2], station[3]))
                try:
                    distance = geo_distance(
                        previous_station[2],
                        previous_station[3],
                        station[2],
                        station[3]
                    )
                    graph.add_edge(previous_station[0],
                                   station[0],
                                   weight=
                                   (distance /
                                   model_parameters.EDGE_COEF[routes_type]),
                                   color=
                                   model_parameters.EDGE_COLOR[routes_type],
                                   type=routes_type
                                   )
                    previous_station = station
                except:
                    previous_station = station
                    continue
        if route[2] == 1 and route_stations and len(route_stations) > 1 and \
                graph.has_node(route_stations[0][0]) and\
                graph.has_node(route_stations[-1][0]):
            distance = geo_distance(
                route_stations[-1][2],
                route_stations[-1][3],
                route_stations[0][2],
                route_stations[0][3]
            )
            graph.add_edge(route_stations[-1][0], route_stations[0][0],
                           weight=
                           (distance /
                            model_parameters.EDGE_COEF[routes_type]),
                           color=model_parameters.EDGE_COLOR[routes_type],
                           type=routes_type)
    return graph


def ways_to_graph(graph, system_id, routes_type, database):
    database.execute('''SELECT id, ref, circle 
                        FROM Route 
                        WHERE system_id = ? AND type = ?''',
                     (system_id, routes_type))
    for route in database.fetchall():
        print('Working on route ' + str(route[1]) + ', id=' +
              str(route[0]) + '...')
        database.execute('SELECT id FROM Way WHERE route_id = ?', (route[0],))
        for way in database.fetchall():
            previous_station = list()
            database.execute('''SELECT id, name, longitude, latitude
                                FROM Station WHERE way_id = ? 
                                ORDER BY way_order''',
                             (way[0],))
            way_nodes = database.fetchall()
            for station in way_nodes:
                if previous_station:
                    graph.add_node(station[0], name=station[1],
                                   pos=(station[2], station[3]))
                    distance = geo_distance(
                        previous_station[2],
                        previous_station[3],
                        nx.get_node_attributes(graph, 'pos')[station[0]][0],
                        nx.get_node_attributes(graph, 'pos')[station[0]][1]
                    )
                    graph.add_edge(previous_station[0],
                                   station[0],
                                   weight=
                                   (distance /
                                   model_parameters.EDGE_COEF[routes_type]),
                                   color=
                                   model_parameters.EDGE_COLOR[routes_type],
                                   type=routes_type
                                   )
                    previous_station = station
                else:
                    graph.add_node(station[0], name=station[1],
                                   pos=(station[2], station[3]))
                    previous_station = station
        database.execute('''SELECT id, name, longitude, latitude, route_id
                            FROM Station WHERE route_id = ? ORDER BY id''',
                         (route[0],))
        route_stations = database.fetchall()
        if route[2] == 1 and route_stations and len(route_stations) > 1 and \
                graph.has_node(route_stations[0][0]) and\
                graph.has_node(route_stations[-1][0]):
            distance = geo_distance(
                route_stations[-1][2],
                route_stations[-1][3],
                route_stations[0][2],
                route_stations[0][3]
            )
            graph.add_edge(route_stations[-1][0], route_stations[0][0],
                           weight=
                           (distance /
                           model_parameters.EDGE_COEF[routes_type]),
                           color=model_parameters.EDGE_COLOR[routes_type],
                           type=routes_type)
    return graph


def fix_edges(database, graph, type):
    print('Trying to fix ' + type + '...')
    coef = {'subway': 2,
            'train': 3,
            'light_rail': 2,
            'tram': 15,
            'bus': 15,
            'trolleybus': 15}
    edges_lengths = list()
    for edge in graph.edges.data():
        if edge[2]['type'] == type:
            edges_lengths.append(edge[2]['weight'])
    if edges_lengths:
        median_length = median(edges_lengths)
    else:
        median_length = 0
    edges_to_remove = list()
    for edge in graph.edges.data():
        if edge[2]['weight'] > median_length * coef[type] and\
                edge[2]['type'] == type:
            database.execute('''SELECT Station.name, Route.ref 
                                FROM Station JOIN Route
                                ON Station.route_id = Route.id
                                WHERE Station.id = ? LIMIT 1''',
                             (edge[0],))
            first_node = database.fetchone()
            database.execute('''SELECT Station.name, Route.ref
                                FROM Station JOIN Route
                                ON Station.route_id = Route.id
                                WHERE Station.id = ? LIMIT 1''',
                             (edge[1],))
            end_node = database.fetchone()
            print(str(first_node[0]) + ' (' + str(first_node[1]) + ') <-> ' +
                  str(end_node[0]) + ' (' + str(end_node[1]) + '), ' +
                  str(round(edge[2]['weight'], 2)) +
                  ' km looks strange to me. Delete it? (Y/N): ', end='')
            decision = input()
            if decision.upper() == 'Y':
                edges_to_remove.append((edge[0], edge[1]))
    for edge in edges_to_remove:
        graph.remove_edge(edge[0], edge[1])
    return graph


def db_cleanup(system_id, graph, database, db_connection):
    # This function is needed as interchanges_to_graph.py iterates over all
    # possible pairs of existing stations and uses some information about
    # those stations from database. Instead of iterating over pairs of nodes
    # and then SELECTing additional info from database each time, we iterate
    # over pairs of stations directly from DB. However, in order to reduce
    # amount of duplicating iterations, especially for heavy rail transit
    # where we ask user to confirm interchanges manually, we need to clean DB
    # and remove duplicating stations downloaded from OSM and removed during
    # graph construction. Refer to interchanges_to_graph.py for more details
    # on interchange addition mechanics.
    database.execute('''SELECT Station.id FROM Station JOIN Route
                        ON Station.route_id = Route.id
                        WHERE Route.system_id = ?''', (system_id,))

    db_stations = set()
    for station in database.fetchall():
        db_stations.add(station[0])
    nodes = set(graph.nodes())

    db_stations_to_delete = list(db_stations - nodes)

    for station in db_stations_to_delete:
        database.execute('DELETE FROM Station WHERE id = ?', (station,))
    db_connection.commit()

    database.execute('VACUUM')
    db_connection.commit()
    return True


# main module starts here with DB connection
db_connection = sqlite3.connect('systems.sqlite')
database = db_connection.cursor()

# retrieve list of cities
database.execute('SELECT id, name FROM RailwaySystem')

for system in database.fetchall():
    # if file with graph already existing in 'raw' directory, proceed further
    if os.path.isfile('raw/' + str(system[1].split(',')[0]) + '.gpickle'):
        print('File with name ' + 'raw/' + str(system[1].split(',')[0]) +
              '.gpickle' + ' already exists!')
        continue
    system_id = system[0]  # getting city system id from DB response
    print('Processing ' + system[1] + ', id=' + str(system_id) + '...')
    system_graph = nx.MultiGraph()  # creating empty graph object
    # Multigraph type is used since sometimes same stops / stations may have few
    # routes between them - ideally this should not be the case after all
    # cleanups but may happen in the middle of graph construction

    # then we gradually add to graph different means of transport. Modular
    # approach is needed since we have different approach for good data
    # quality heavy rail and low data quality overground transport, and also
    # to make debug easier
    system_graph = routes_to_graph(system_graph, system_id, 'subway',
                                   database)
    system_graph = routes_to_graph(system_graph, system_id, 'train',
                                   database)
    system_graph = routes_to_graph(system_graph, system_id, 'light_rail',
                                   database)
    system_graph = ways_to_graph(system_graph, system_id, 'tram',
                                 database)
    system_graph = ways_to_graph(system_graph, system_id, 'bus',
                                 database)
    system_graph = ways_to_graph(system_graph, system_id, 'trolleybus',
                                 database)

    print('Now let me try to find some *probably* mistakenly added edges and'
          ' suggest you to remove them:')

    # then we are trying to fix edges in modular way to account for different
    # level of possible 'weirdness' for different means of transport
    system_graph = fix_edges(database, system_graph, 'subway')
    system_graph = fix_edges(database, system_graph, 'train')
    system_graph = fix_edges(database, system_graph, 'light_rail')
    system_graph = fix_edges(database, system_graph, 'tram')
    system_graph = fix_edges(database, system_graph, 'bus')
    system_graph = fix_edges(database, system_graph, 'trolleybus')

    # then we clean up database based on final graph object
    db_cleanup(system_id, system_graph, database, db_connection)

    # finally we write resulting graph in Gpickle file object that can be
    # reused further
    nx.write_gpickle(system_graph, 'raw/' + str(system[1].split(',')[0]) +
                     '.gpickle')
    print('Done, all routes and ways are added to /raw directory as'
          ' non-connected graphs. Now run interchanges_to_graph.py to add all'
          ' interchanges!')

db_connection.close()  # closing connection with SQLite

# urban rail should actually have the same weight as subway urbal rail add nodes only within bounding box
# в формуле нужно учесть еще и маршрутную скорость
# overground должен увеличивать вес быстрее чем остальные в зависимости от дистанции
# посчитать сколько ресурсов займет расчет одного графа?
# переписать механизм расчета пересадок - исключить SELECT для каждой пересадки, убрать interchange name (зачем она?)
# merge'ить по name и distance
# для subway, train, light_rail - выгружать такие станции, но искать combinations только их с ними
# additional check for mergers on final graph
