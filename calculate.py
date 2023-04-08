import time
import networkx as nx
import sqlite3
from itertools import combinations
from itertools import chain
from get_distance import geo_distance
import operator


def path_length(path):
    real_distance = 0
    for i in range(1, len(path)):
        try:
            real_distance += edge_length[(path[i - 1], path[i], 0)]
        except KeyError:
            try:
                real_distance += edge_length[(path[i], path[i - 1], 0)]
            except KeyError:
                print('Something went wrong and this message should have never appeared. Though path',
                      pair[0],
                      'to',
                      pair[1],
                      'exists, there is no edge weight between path members',
                      ath[i],
                      'and',
                      path[i - 1])
                continue
    return real_distance


def spread_index(system_id, system_graph, database, db_connection):
    avg_path_cumulative = 0
    i = 0
    for pair in combinations(system_graph.nodes(), 2):
        if pair[0] == pair[1]:
            continue
        try:
            current_path = paths[pair[0]][pair[1]]
        except KeyError:
            continue
        avg_path_cumulative += path_length(current_path)
        i += 1
    return avg_path_cumulative / (i * system_graph.number_of_nodes())


def find_shortest_paths(system_id, system_graph, database, db_connection, paths):

    position = nx.get_node_attributes(system_graph, 'pos')
    edge_length = nx.get_edge_attributes(system_graph, 'weight')

    max_direct_distance = 0

    for pair in combinations(system_graph.nodes(), 2):
        if pair[0] == pair[1]:
            continue
        try:
            current_path = paths[pair[0]][pair[1]]
        except KeyError:
            # for some reason there still may be few components in the graph
            # но это не оч страшно, потому что мы optimality взвешивем по расстоянию direct_distance
            continue
        direct_distance = geo_distance(position[pair[0]][0],
                                       position[pair[0]][1],
                                       position[pair[1]][0],
                                       position[pair[1]][1])
        if direct_distance < 1.5:
            continue

        if direct_distance >= max_direct_distance:
            max_direct_distance = direct_distance

        optimality = direct_distance / path_length(current_path)
        path_csv = ','.join(map(str, current_path))
        database.execute('''INSERT OR IGNORE INTO Path (system_id, station_from, station_to, real_distance, 
                        direct_distance, optimality, steps)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                         (
                             system_id,
                             pair[0],
                             pair[1],
                             real_distance,
                             direct_distance,
                             optimality,
                             path_csv
                         )
                         )

    db_connection.commit()
    return max_direct_distance


start_time = time.time()

db_connection = sqlite3.connect('systems.sqlite')
database = db_connection.cursor()

database.executescript('''
    CREATE TABLE IF NOT EXISTS Path (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        system_id INTEGER,
        station_from INTEGER,
        station_to INTEGER,
        real_distance REAL,
        direct_distance REAL,
        optimality REAL,
        inv_weighted_optimality REAL,
        steps TEXT UNIQUE
    );
''')

system_graph = nx.read_gpickle('final/' + input('Enter city to calculate over the graph: ') + '.gpickle')

for node in system_graph.nodes():
    database.execute('''SELECT RailwaySystem.id FROM Station JOIN Route JOIN RailwaySystem
                        ON Station.route_id = Route.id AND Route.system_id = RailwaySystem.id 
                        WHERE Station.id = ? LIMIT 1''', (node,))
    break

system_id = database.fetchone()[0]

print('System size:', len(system_graph.nodes), 'nodes', sep=' ')
print('Finding all shortest paths, may take a while...')
paths = dict(nx.all_pairs_dijkstra_path(system_graph, weight='weight'))
print('Found! Now calculating indices, will take even more time...')

max_distance = find_shortest_paths(system_id, system_graph, database, db_connection, paths)

database.execute('UPDATE Path SET inv_weighted_optimality = (optimality / (direct_distance / ?)) WHERE system_id = ?',
                 (max_distance, system_id))
db_connection.commit()

database.execute('SELECT optimality FROM Path WHERE system_id = ? ORDER BY id', (system_id,))
optimality = list(chain(*database.fetchall()))
database.execute('SELECT direct_distance FROM Path WHERE system_id = ? ORDER BY id', (system_id,))
weights = list(chain(*database.fetchall()))

optimality_indx = sum(map(operator.mul, optimality, weights)) / sum(weights)

print('City optimality index =', round(optimality_indx, 3))

database.execute('UPDATE RailwaySystem SET optimality_indx = ? WHERE id = ?', (optimality_indx, system_id))

s_index = spread_index(system_id, system_graph, database, db_connection, paths)

print('Spread index =', round(s_index, 4))

database.execute('UPDATE RailwaySystem SET s_index = ? WHERE id = ?', (s_index, system_id))

db_connection.commit()
db_connection.close()

print('Done, time elapsed: {:.2f}s'.format(time.time() - start_time))
