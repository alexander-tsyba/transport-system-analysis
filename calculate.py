import time
import networkx as nx
import sqlite3
from itertools import combinations
from itertools import chain
from get_distance import geo_distance
import operator


def find_shortest_paths(system_id, system_graph, database, db_connection):
    print('Finding all shortest paths, may take a while...')
    path = dict(nx.all_pairs_dijkstra_path(system_graph, weight='weight'))
    print('Found! Now calculating indices, will take even more time...')

    position = nx.get_node_attributes(system_graph, 'pos')
    edge_length = nx.get_edge_attributes(system_graph, 'weight')

    max_direct_distance = 0

    for pair in combinations(system_graph.nodes(), 2):
        if pair[0] == pair[1]:
            continue
        try:
            current_path = path[pair[0]][pair[1]]
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

        real_distance = 0
        for i in range(1, len(current_path)):
            try:
                real_distance += edge_length[(current_path[i - 1], current_path[i], 0)]
            except KeyError:
                try:
                    real_distance += edge_length[(current_path[i], current_path[i - 1], 0)]
                except KeyError:
                    print('Something went wrong and this message should have never appeared. Though path',
                          pair[0],
                          'to',
                          pair[1],
                          'exists, there is no edge weight between path members',
                          current_path[i],
                          'and',
                          current_path[i - 1])
                    continue
        optimality = direct_distance / real_distance
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

max_distance = find_shortest_paths(system_id, system_graph, database, db_connection)

database.execute('UPDATE Path SET inv_weighted_optimality = (optimality / (direct_distance / ?)) WHERE system_id = ?',
                 (max_distance, system_id))
db_connection.commit()
# inv weighted optimaluty - для плохих и длинных маршрутов

database.execute('SELECT optimality FROM Path WHERE system_id = ? ORDER BY id', (system_id,))
optimality = list(chain(*database.fetchall()))
database.execute('SELECT direct_distance FROM Path WHERE system_id = ? ORDER BY id', (system_id,))
weights = list(chain(*database.fetchall()))

optimality_indx = sum(map(operator.mul, optimality, weights)) / sum(weights)

print('City optimality index =', round(optimality_indx, 3))

database.execute('UPDATE RailwaySystem SET optimality_indx = ? WHERE id = ?', (optimality_indx, system_id))
db_connection.commit()
db_connection.close()

print('Done, time elapsed: {:.2f}s'.format(time.time() - start_time))

# if no path -> continue фиг с ним
# path_distance = edges weights in path
# средняя скорость метро 40

# ДОБАВЛЯТЬ ВЕСА на этапе создания графа!
# train - 45 coef to subway = делить на 1.125
# lrt - 30 - делить на 0.75
# tram - 20 - делить на 0.5
# bus - 15 - делить на 0.375
# trolleybus - 15 - делить на 0.375

# пересадки - по хорошему, надо как то более системно считать - либо по времени, либо проводить опросы и понимать, какова цена "неудобства" при пересадке
# R - по опросам, равно 4 перегона метро - метро в 10 раз быстрее пешего шага - примерно как 6 км на метро
# O - R (6000) умножить на distance / 4 km/h / 5 min
# X - по логике, как минимум это равно 1 перегону метро - 1.5 км

# в моей модели не учитывается перегрузка перегонов! можно бы было ввести доп коэффициент, но в идеальной модели
# человек принимает решение по скорости, перегрузка тоже может повлиять, но для этого нужно в модель вставить реальные потоки
# так как мы не знаем, в основном где начинаются и заканчиваются маршруты

# по хорошему, для каждого города нужно свою маршрутную скорость вставлять
# add node type to graphs, чтобы в формуле interchanges вставлять доп коэффициенты отражающие средний интервал станции на которую пересадка

# средние интервалы - тоже взял усредненные. Но модель может понять помочь, где урбанистам нужно проверить интервалы!
# модель поможет понять узкие места и проанализировать их более детально со всех точек зрения - вид транспорта, пересадки, интервалы, связность и т д
# vs просто построение маршрутов в google api distance matrix - независимый алгоритм, который не ведет через заранее определенные места
# + it is free and highly customizable

# bus / tbs - 5 veichles per hour - 6 минут в среднем * 667
# tram - 6 vechiles per hour
# lrt - 12 veichles per hour
# subway - 20 veichles per hour
# train - 6 vechiles per hour

# на будущее - механизм чистки лишних interchanges
# добавлять к станции атрибут - в скольких она коротких путях
# разная длина пересадок 700 и 100 метров - стимулирует пользование метро - насколько это верно?
# нас интересуют машруты от 1.5 км и более, в локальных связках копаться... надо тогда на api сравнивать, можно ли пройти напрямую
