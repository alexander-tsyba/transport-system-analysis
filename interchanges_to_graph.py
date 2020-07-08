import networkx as nx
import sqlite3
import os.path
from get_distance import geo_distance
from itertools import combinations
from itertools import product

# not efficient stepping in get_paths

# for tram / bus / trolleybus that can connect to subway, train, light_rail
def way_auto_interchanges_to_graph(system_id, graph, database):
    waiting_coef = {
        'subway': (1.5 * 667) / 1000,
        'train': (5 * 667) / 1000,
        'light_rail': (2.5 * 667) / 1000,
        'tram': (5 * 667) / 1000,
        'bus': (6 * 667) / 1000,
        'trolleybus': (6 * 667) / 1000,
    }

    database.execute('''SELECT Station.id, Station.longitude, Station.latitude, Station.name,
                        Route.ref, Route.type
                        FROM Station JOIN Route ON Station.route_id = Route.id
                        WHERE Route.system_id = ? 
                        AND (Route.type = 'subway' OR Route.type = 'train' OR Route.type = 'light_rail')
                        ''', (system_id,))
    stations = database.fetchall()

    database.execute('''SELECT Station.id, Station.longitude, Station.latitude, Station.name,
                        Route.ref, Route.type
                        FROM Station JOIN Route ON Station.route_id = Route.id
                        WHERE Route.system_id = ? 
                        AND (Route.type = 'bus' OR Route.type = 'tram' OR Route.type = 'trolleybus')
                        ''', (system_id,))
    nodes = database.fetchall()

    node_pairs = list(combinations(nodes, 2))

    i = 0
    total_steps = len(node_pairs)

    nodes_to_merge = list()

    for pair in node_pairs:
        transfer_max_length = 0.15
        station_from = pair[0]
        station_to = pair[1]

        if graph.has_edge(station_from[0], station_to[0]):
            i += 1
            continue

        distance = geo_distance(station_from[1], station_from[2], station_to[1], station_to[2])

        if distance <= transfer_max_length:
            if station_from[3] == station_to[3] or distance <= 0:
                nodes_to_merge.append((station_from[0], station_to[0]))
            elif (station_from[5] != station_to[5] or
                  (station_from[5] == station_to[5] and station_from[4] != station_to[4])) and \
                    graph.has_node(station_from[0]) and graph.has_node(station_to[0]):
                graph.add_edge(station_from[0], station_to[0],
                               weight=((distance / 67) / 5) * 6 + waiting_coef[station_to[5]],
                               type='interchange',
                               color='green')  # length of interchage divide by walking speed (67 meters per minute) divide by average time to do regular change (5 mins) times weight of regular change
        i += 1
        if i % 5000 == 0:
            print('Overall way-like interchange progress: ' + str(i) + '/' + str(total_steps) +
                  ' (' + str(round(i / total_steps * 100, 2)) + '%)')

    station_node_pairs = list(product(stations, nodes))

    i = 0
    total_steps = len(station_node_pairs)

    for pair in station_node_pairs:
        transfer_max_length = 0.5
        station_from = pair[0]
        station_to = pair[1]

        if graph.has_edge(station_from[0], station_to[0]):
            i += 1
            continue

        distance = geo_distance(station_from[1], station_from[2], station_to[1], station_to[2])

        if distance <= transfer_max_length and graph.has_node(station_from[0]) and graph.has_node(station_to[0]):
            graph.add_edge(station_from[0], station_to[0],
                           weight=((distance / 67) / 5) * 6 + waiting_coef[station_to[5]],
                           type='interchange',
                           color='green')  # length of interchage divide by walking speed (67 meters per minute) divide by average time to do regular change (5 mins) times weight of regular change
        i += 1
        if i % 5000 == 0:
            print('Overall station_node-like interchange progress: ' + str(i) + '/' + str(total_steps) +
                  ' (' + str(round(i / total_steps * 100, 2)) + '%)')

    i = 0
    total_steps = len(nodes_to_merge)

    for mergers in nodes_to_merge:

        distances = nx.get_edge_attributes(graph, 'weight')
        routes_type = nx.get_edge_attributes(graph, 'type')

        if graph.has_node(mergers[1]):
            for neighbour in nx.all_neighbors(graph, mergers[1]):
                add_edge_with_neighbour = False
                if graph.has_edge(neighbour, mergers[0]):
                    try:
                        existing_edge_type = routes_type[(neighbour, mergers[0], 0)]
                    except KeyError:
                        existing_edge_type = routes_type[(mergers[0], neighbour, 0)]
                    if existing_edge_type == 'interchange':
                        add_edge_with_neighbour = True
                        graph.remove_edge(neighbour, mergers[0])
                if (not graph.has_edge(neighbour, mergers[0])) or add_edge_with_neighbour:
                    try:
                        distance = distances[(neighbour, mergers[1], 0)]
                        route_type = routes_type[(neighbour, mergers[1], 0)]
                    except KeyError:
                        distance = distances[(mergers[1], neighbour, 0)]
                        route_type = routes_type[(mergers[1], neighbour, 0)]
                    graph.add_edge(neighbour, mergers[0], weight=distance,
                                   type=route_type)
            graph.remove_node(mergers[1])

        i += 1
        if i % 100 == 0:
            print('Overall merging progress: ' + str(i) + '/' + str(total_steps) +
                  ' (' + str(round(i / total_steps * 100, 2)) + '%)')

    return graph


# manual script only for subway, train, light_rail but without SQL now
def interchanges_to_graph(system_id, graph, database):
    waiting_coef = {
        'subway': (1.5 * 667) / 1000,
        'train': (5 * 667) / 1000,
        'light_rail': (2.5 * 667) / 1000
    }

    database.execute('''SELECT Station.id, Station.longitude, Station.latitude, Station.name,
                        Route.ref, Route.type
                        FROM Station JOIN Route ON Station.route_id = Route.id
                        WHERE Route.system_id = ? 
                        AND (Route.type = 'subway' OR Route.type = 'train' OR Route.type = 'light_rail')
                        ''', (system_id,))
    stations = database.fetchall()

    pairs = list(combinations(stations, 2))

    i = 0
    total_steps = len(pairs)

    stations_to_merge = list()

    for pair in pairs:
        transfer_max_length = 0.7
        station_from = pair[0]
        station_to = pair[1]

        if graph.has_edge(station_from[0], station_to[0]):
            i += 1
            continue

        distance = geo_distance(station_from[1], station_from[2], station_to[1], station_to[2])

        if distance <= transfer_max_length:
            interchange_from = str(station_from[3]) + ' (' + str(station_from[5]) + ', ' + str(station_from[4]) + ')'
            interchange_to = str(station_to[3]) + ' (' + str(station_to[5]) + ', ' + str(station_to[4]) + ')'
            interchange_name = interchange_from + ' <-> ' + interchange_to
            if interchange_from == interchange_to:
                stations_to_merge.append((station_from[0], station_to[0]))
                print(interchange_name + ', merging automatically...')
                continue
            else:
                print(interchange_name + "? (R[regular]/O[overground]/X[crossplatform]/M[merge] or N[none]): ", end="")
                decision = input()
            if decision.upper() == 'R' and graph.has_node(station_from[0]) and graph.has_node(station_to[0]):
                graph.add_edge(station_from[0], station_to[0], weight=4 + waiting_coef[station_to[5]],
                               type='interchange')
            elif decision.upper() == 'O' and graph.has_node(station_from[0]) and graph.has_node(station_to[0]):
                graph.add_edge(station_from[0], station_to[0],
                               weight=((distance / 67) / 5) * 6 + waiting_coef[station_to[5]],
                               type='interchange')  # length of interchage divide by walking speed (67 meters per minute) divide by average time to do regular change (5 mins) times weight of regular change
            elif decision.upper() == 'X' and graph.has_node(station_from[0]) and graph.has_node(station_to[0]):
                graph.add_edge(station_from[0], station_to[0], weight=1.5 + waiting_coef[station_to[5]],
                               type='interchange')
            elif decision.upper() == 'M' and graph.has_node(station_from[0]) and graph.has_node(station_to[0]):
                stations_to_merge.append((station_from[0], station_to[0]))
        i += 1
        if i % 5000 == 0:
            print('Overall route-like interchange progress: ' + str(i) + '/' + str(total_steps) +
                  ' (' + str(round(i / total_steps * 100, 2)) + '%)')

    for mergers in stations_to_merge:
        distances = nx.get_edge_attributes(graph, 'weight')
        routes_type = nx.get_edge_attributes(graph, 'type')
        if graph.has_node(mergers[1]):
            for neighbour in nx.all_neighbors(graph, mergers[1]):
                add_edge_with_neighbour = False
                if graph.has_edge(neighbour, mergers[0]):
                    try:
                        existing_edge_type = routes_type[(neighbour, mergers[0], 0)]
                    except KeyError:
                        existing_edge_type = routes_type[(mergers[0], neighbour, 0)]
                    if existing_edge_type == 'interchange':
                        add_edge_with_neighbour = True
                        graph.remove_edge(neighbour, mergers[0])
                if (not graph.has_edge(neighbour, mergers[0])) or add_edge_with_neighbour:
                    try:
                        distance = distances[(neighbour, mergers[1], 0)]
                        route_type = routes_type[(neighbour, mergers[1], 0)]
                    except KeyError:
                        distance = distances[(mergers[1], neighbour, 0)]
                        route_type = routes_type[(mergers[1], neighbour, 0)]
                    graph.add_edge(neighbour, mergers[0], weight=distance,
                                   type=route_type)
            graph.remove_node(mergers[1])

    return graph


# obsolete function using SQL result - DO NOT USE
def zz_interchanges_to_graph(system_id, graph, database):
    database.execute('SELECT * FROM Interchange WHERE system_id = ?', (system_id,))
    # waiting coef - сколько можно проехать км на метро, пока ждешь поезда на станции
    waiting_coef = {
        'subway': (1.5 * 667) / 1000,
        'train': (5 * 667) / 1000,
        'light_rail': (2.5 * 667) / 1000,
        'tram': (5 * 667) / 1000,
        'bus': (6 * 667) / 1000,
        'trolleybus': (6 * 667) / 1000,
    }
    for interchange in database.fetchall():
        database.execute('''SELECT Route.type FROM Station JOIN Route 
                            ON Station.route_id = Route.id WHERE Station.id = ? LIMIT 1''', (interchange[3],))
        station_to_type = database.fetchone()[0]
        if interchange[5] == 'R' and graph.has_node(interchange[2]) and graph.has_node(interchange[3]):
            graph.add_edge(interchange[2], interchange[3], weight=4 + waiting_coef[station_to_type], type='interchange',
                           color='green')
        elif interchange[5] == 'O' and graph.has_node(interchange[2]) and graph.has_node(interchange[3]):
            graph.add_edge(interchange[2], interchange[3],
                           weight=((interchange[4] / 67) / 5) * 6 + waiting_coef[station_to_type], type='interchange',
                           color='green')  # length of interchage divide by walking speed (67 meters per minute) divide by average time to do regular change (5 mins) times weight of regular change
        elif interchange[5] == 'X' and graph.has_node(interchange[2]) and graph.has_node(interchange[3]):
            graph.add_edge(interchange[2], interchange[3], weight=1.5 + waiting_coef[station_to_type],
                           type='interchange',
                           color='green')
    return graph


# obsolete function using SQL result - DO NOT USE
def zz_merge_adjacent_nodes(system_id, graph, database, db_connection):
    database.execute('SELECT station_id_from, station_id_to FROM Interchange WHERE system_id = ? AND type = ?',
                     (system_id, 'M'))
    edge_color = {
        'subway': 'black',
        'train': 'blue',
        'light_rail': 'cyan',
        'tram': 'magenta',
        'bus': 'red',
        'trolleybus': 'red'
    }
    for mergers in database.fetchall():

        database.execute('SELECT * FROM Interchange WHERE station_id_from <> ? AND station_id_to = ?',
                         (mergers[0], mergers[1]))
        existing_interchanges = database.fetchall()
        for interchanges in existing_interchanges:
            database.execute('SELECT * FROM Interchange WHERE station_id_from = ? AND station_id_to = ? LIMIT 1',
                             (interchanges[2], mergers[0]))
            if not database.fetchone():
                database.execute('''INSERT INTO Interchange (name, station_id_from, station_id_to, length, type, system_id)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                                 (
                                     str(interchanges[2]) + ' to ' + str(mergers[0]),
                                     interchanges[2],
                                     mergers[0],
                                     interchanges[4],
                                     interchanges[5],
                                     system_id
                                 )
                                 )
                db_connection.commit()

        database.execute('SELECT * FROM Interchange WHERE station_id_from = ? AND station_id_to <> ?',
                         (mergers[1], mergers[0]))
        existing_interchanges = database.fetchall()
        for interchanges in existing_interchanges:
            database.execute('SELECT * FROM Interchange WHERE station_id_from = ? AND station_id_to = ? LIMIT 1',
                             (mergers[0], interchanges[3]))
            if not database.fetchone():
                database.execute('''INSERT INTO Interchange (name, station_id_from, station_id_to, length, type, system_id)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                                 (
                                     str(mergers[0]) + ' to ' + str(interchanges[3]),
                                     mergers[0],
                                     interchanges[3],
                                     interchanges[4],
                                     interchanges[5],
                                     system_id
                                 )
                                 )
                db_connection.commit()
        database.execute('DELETE FROM Interchange WHERE station_id_to = ? AND station_id_from <> ?',
                         (mergers[1], mergers[0]))
        database.execute('DELETE FROM Interchange WHERE station_id_from = ?', (mergers[1],))

        if graph.has_node(mergers[1]):
            for neighbour in nx.all_neighbors(graph, mergers[1]):
                if not graph.has_edge(neighbour, mergers[0]):
                    try:
                        distance = nx.get_edge_attributes(graph, 'weight')[(neighbour, mergers[1], 0)]
                        routes_type = nx.get_edge_attributes(graph, 'type')[(neighbour, mergers[1], 0)]
                    except KeyError:
                        distance = nx.get_edge_attributes(graph, 'weight')[(mergers[1], neighbour, 0)]
                        routes_type = nx.get_edge_attributes(graph, 'type')[(mergers[1], neighbour, 0)]
                    graph.add_edge(neighbour, mergers[0], weight=distance, color=edge_color[routes_type],
                                   type=routes_type)
            graph.remove_node(mergers[1])
    return graph


db_connection = sqlite3.connect('systems.sqlite')
database = db_connection.cursor()

database.execute('SELECT id, name FROM RailwaySystem')

for system in database.fetchall():
    if os.path.isfile('final/' + str(system[1].split(',')[0]) + '.gpickle'):
        print('File with name ' + 'final/' + str(system[1].split(',')[0]) + '.gpickle' + ' already exists!')
        continue
    system_id = system[0]
    system_graph = nx.read_gpickle('raw/' + str(system[1].split(',')[0]) + '.gpickle')

    print('Confirm interchanges in ' + system[1] + ':')
    system_graph = interchanges_to_graph(system_id, system_graph, database)
    system_graph = way_auto_interchanges_to_graph(system_id, system_graph, database)
    db_connection.commit()

    print('Done adding manual + auto interchanges and merging adjacent nodes!')
    print('Now run calculate.py or calculate_auto.py to calculate shortest paths and optimality over the graph')

    nx.write_gpickle(system_graph, 'final/' + str(system[1].split(',')[0]) + '.gpickle')

db_connection.close()
