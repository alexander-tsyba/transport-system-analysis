from get_distance import geo_distance
import networkx as nx
import sqlite3
from statistics import median
import os.path


def routes_to_graph(graph, system_id, routes_type, database):
    database.execute('SELECT id, ref, circle FROM Route WHERE system_id = ? AND type = ?', (system_id, routes_type))
    edge_coef = {'subway': 1,
                 'train': 1.125,
                 'light_rail': 0.75
                 }
    edge_color = {
        'subway': 'black',
        'train': 'blue',
        'light_rail': 'cyan',
        'tram': 'magenta',
        'bus': 'red',
        'trolleybus': 'red'
    }
    for route in database.fetchall():
        previous_station = list()
        print('Working on route ' + str(route[1]) + ', id=' + str(route[0]) + '...')
        database.execute('SELECT id, name, longitude, latitude, route_id FROM Station WHERE route_id = ? ORDER BY id',
                         (route[0],))
        route_stations = database.fetchall()
        index = -1
        for station in route_stations:
            index += 1
            station_already_exists_id = 0
            station_already_exists_id_route_id = 0
            database.execute('''SELECT Station.id, Route.id
                                FROM Station JOIN Route JOIN RailwaySystem 
                                ON Station.route_id = Route.id AND Route.system_id = RailwaySystem.id 
                                WHERE Station.name = ? AND Station.id <> ? AND Route.ref = ? AND RailwaySystem.id = ?
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
                                    WHERE Station.name = ? AND Station.longitude = ? AND Station.latitude = ? 
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
                                        WHERE Station.name = ? AND Station.longitude <> ? AND Station.latitude <> ? 
                                        AND Route.ref <> ?
                                        ORDER BY Station.id''',
                                     (station[1], station[2], station[3], route[1]))
                    for adjacent_existing_stations in database.fetchall():
                        exit_cycle_2 = False
                        if graph.has_node(adjacent_existing_stations[0]):
                            neighbours_of_existing_node = nx.all_neighbors(graph, adjacent_existing_stations[0])
                            for neighbour in neighbours_of_existing_node:
                                neighbour_name = nx.get_node_attributes(graph, 'name')[neighbour]
                                if previous_station and index + 1 < len(route_stations):
                                    if neighbour_name == previous_station[1] or neighbour_name == \
                                            route_stations[index + 1][1]:
                                        station_already_exists_id = adjacent_existing_stations[0]
                                        station_already_exists_id_route_id = adjacent_existing_stations[1]
                                        exit_cycle = True
                                        exit_cycle_2 = True
                                        break
                                elif previous_station and index + 1 >= len(route_stations):
                                    if neighbour_name == previous_station[1]:
                                        station_already_exists_id = adjacent_existing_stations[0]
                                        station_already_exists_id_route_id = adjacent_existing_stations[1]
                                        exit_cycle = True
                                        exit_cycle_2 = True
                                        break
                            if exit_cycle_2:
                                break
                    if exit_cycle:
                        break
            if station_already_exists_id != 0:
                if (not previous_station) or graph.has_edge(previous_station[0], station_already_exists_id):
                    database.execute('SELECT id, name, longitude, latitude, route_id FROM Station WHERE id = ? LIMIT 1',
                                     (station_already_exists_id,))
                    previous_station = database.fetchone()
                    continue
                elif not graph.has_edge(previous_station[0], station_already_exists_id) and \
                        previous_station[4] == station_already_exists_id_route_id:
                    database.execute('SELECT id, name, longitude, latitude, route_id FROM Station WHERE id = ? LIMIT 1',
                                     (station_already_exists_id,))
                    previous_station = database.fetchone()
                    continue
                else:
                    distance = geo_distance(
                        previous_station[2],
                        previous_station[3],
                        nx.get_node_attributes(graph, 'pos')[station_already_exists_id][0],
                        nx.get_node_attributes(graph, 'pos')[station_already_exists_id][1]
                    )
                    graph.add_edge(previous_station[0],
                                   station_already_exists_id,
                                   weight=distance / edge_coef[routes_type],
                                   color=edge_color[routes_type],
                                   type=routes_type
                                   )
                    database.execute('SELECT id, name, longitude, latitude, route_id FROM Station WHERE id = ? LIMIT 1',
                                     (station_already_exists_id,))
                    previous_station = database.fetchone()
            else:
                graph.add_node(station[0], name=station[1], pos=(station[2], station[3]))
                try:
                    distance = geo_distance(
                        previous_station[2],
                        previous_station[3],
                        station[2],
                        station[3]
                    )
                    graph.add_edge(previous_station[0],
                                   station[0],
                                   weight=distance / edge_coef[routes_type],
                                   color=edge_color[routes_type],
                                   type=routes_type
                                   )
                    previous_station = station
                except:
                    previous_station = station
                    continue
        if route[2] == 1 and route_stations and len(route_stations) > 1 and \
                graph.has_node(route_stations[0][0]) and graph.has_node(route_stations[-1][0]):
            distance = geo_distance(
                route_stations[-1][2],
                route_stations[-1][3],
                route_stations[0][2],
                route_stations[0][3]
            )
            graph.add_edge(route_stations[-1][0], route_stations[0][0],
                           weight=distance / edge_coef[routes_type],
                           color=edge_color[routes_type],
                           type=routes_type)
    return graph


def ways_to_graph(graph, system_id, routes_type, database):
    database.execute('SELECT id, ref, circle FROM Route WHERE system_id = ? AND type = ?', (system_id, routes_type))
    edge_coef = {'tram': 0.5,
                 'bus': 0.375,
                 'trolleybus': 0.375
                 }
    edge_color = {
        'subway': 'black',
        'train': 'blue',
        'light_rail': 'cyan',
        'tram': 'magenta',
        'bus': 'red',
        'trolleybus': 'red'
    }
    for route in database.fetchall():
        print('Working on route ' + str(route[1]) + ', id=' + str(route[0]) + '...')
        database.execute('SELECT id FROM Way WHERE route_id = ?', (route[0],))
        for way in database.fetchall():
            previous_station = list()
            database.execute('SELECT id, name, longitude, latitude FROM Station WHERE way_id = ? ORDER BY way_order',
                             (way[0],))
            way_nodes = database.fetchall()
            for station in way_nodes:
                if previous_station:
                    graph.add_node(station[0], name=station[1], pos=(station[2], station[3]))
                    distance = geo_distance(
                        previous_station[2],
                        previous_station[3],
                        nx.get_node_attributes(graph, 'pos')[station[0]][0],
                        nx.get_node_attributes(graph, 'pos')[station[0]][1]
                    )
                    graph.add_edge(previous_station[0],
                                   station[0],
                                   weight=distance / edge_coef[routes_type],
                                   color=edge_color[routes_type],
                                   type=routes_type
                                   )
                    previous_station = station
                else:
                    graph.add_node(station[0], name=station[1], pos=(station[2], station[3]))
                    previous_station = station
        database.execute('SELECT id, name, longitude, latitude, route_id FROM Station WHERE route_id = ? ORDER BY id',
                         (route[0],))
        route_stations = database.fetchall()
        if route[2] == 1 and route_stations and len(route_stations) > 1 and \
                graph.has_node(route_stations[0][0]) and graph.has_node(route_stations[-1][0]):
            distance = geo_distance(
                route_stations[-1][2],
                route_stations[-1][3],
                route_stations[0][2],
                route_stations[0][3]
            )
            graph.add_edge(route_stations[-1][0], route_stations[0][0],
                           weight=distance / edge_coef[routes_type],
                           color=edge_color[routes_type],
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
        if edge[2]['weight'] > median_length * coef[type] and edge[2]['type'] == type:
            database.execute('''SELECT Station.name, Route.ref FROM Station JOIN Route
                                ON Station.route_id = Route.id WHERE Station.id = ? LIMIT 1''',
                             (edge[0],))
            first_node = database.fetchone()
            database.execute('''SELECT Station.name, Route.ref FROM Station JOIN Route
                                ON Station.route_id = Route.id WHERE Station.id = ? LIMIT 1''',
                             (edge[1],))
            end_node = database.fetchone()
            print(str(first_node[0]) + ' (' + str(first_node[1]) + ') <-> ' + str(end_node[0]) +
                  ' (' + str(end_node[1]) + '), ' + str(round(edge[2]['weight'], 2)) +
                  ' km looks strange to me. Delete it? (Y/N): ', end='')
            decision = input()
            if decision.upper() == 'Y':
                edges_to_remove.append((edge[0], edge[1]))
    for edge in edges_to_remove:
        graph.remove_edge(edge[0], edge[1])
    return graph


def db_cleanup(system_id, graph, database, db_connection):
    database.execute('''SELECT Station.id FROM Station JOIN Route
                        ON Station.route_id = Route.id WHERE Route.system_id = ?''', (system_id,))

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


db_connection = sqlite3.connect('systems.sqlite')
database = db_connection.cursor()

database.execute('SELECT id, name FROM RailwaySystem')

for system in database.fetchall():
    if os.path.isfile('raw/' + str(system[1].split(',')[0]) + '.gpickle'):
        print('File with name ' + 'raw/' + str(system[1].split(',')[0]) + '.gpickle' + ' already exists!')
        continue
    system_id = system[0]
    print('Processing ' + system[1] + ', id=' + str(system_id) + '...')
    system_graph = nx.MultiGraph()

    system_graph = routes_to_graph(system_graph, system_id, 'subway', database)
    system_graph = routes_to_graph(system_graph, system_id, 'train', database)
    system_graph = routes_to_graph(system_graph, system_id, 'light_rail', database)
    system_graph = ways_to_graph(system_graph, system_id, 'tram', database)
    system_graph = ways_to_graph(system_graph, system_id, 'bus', database)
    system_graph = ways_to_graph(system_graph, system_id, 'trolleybus', database)

    print('Now let me try to find some *probably* mistakenly added edges and suggest you to remove them:')

    system_graph = fix_edges(database, system_graph, 'subway')
    system_graph = fix_edges(database, system_graph, 'train')
    system_graph = fix_edges(database, system_graph, 'light_rail')
    system_graph = fix_edges(database, system_graph, 'tram')
    system_graph = fix_edges(database, system_graph, 'bus')
    system_graph = fix_edges(database, system_graph, 'trolleybus')

    db_cleanup(system_id, system_graph, database, db_connection)

    nx.write_gpickle(system_graph, 'raw/' + str(system[1].split(',')[0]) + '.gpickle')
    print('Done, all routes and ways are added to /raw directory as non-connected graphs. Now run interchanges_to_graph.py to add all interchanges!')

db_connection.close()

# urban rail should actually have the same weight as subway urbal rail add nodes only within bounding box
# в формуле нужно учесть еще и маршрутную скорость
# overground должен увеличивать вес быстрее чем остальные в зависимости от дистанции
# посчитать сколько ресурсов займет расчет одного графа?
# переписать механизм расчета пересадок - исключить SELECT для каждой пересадки, убрать interchange name (зачем она?)
# merge'ить по name и distance
# для subway, train, light_rail - выгружать такие станции, но искать combinations только их с ними
# additional check for mergers on final graph
