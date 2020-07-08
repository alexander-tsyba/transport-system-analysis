import sqlite3
from datetime import datetime
from draw_graph import draw_network_tofile
import networkx as nx
import os


def get_paths(output_type, direct_distance_bottom_limit, direct_distance_upper_limit, optimality_bottom_limit,
              optimality_upper_limit, system_graph, database, foldername):

    database.execute('''SELECT id, direct_distance, optimality, steps
                        FROM Path WHERE direct_distance BETWEEN ? AND ? 
                        AND optimality BETWEEN ? AND ?
                        ORDER BY optimality LIMIT 1''', (direct_distance_bottom_limit,
                                                         direct_distance_upper_limit,
                                                         optimality_bottom_limit,
                                                         optimality_upper_limit))

    path = database.fetchone()

    if path is None:
        return True

    if output_type.upper() == 'F':

        distances = nx.get_edge_attributes(system_graph, 'weight')
        routes_type = nx.get_edge_attributes(system_graph, 'type')

        with open(foldername + '/result.txt', 'a+', encoding='utf8') as file:
            path_nodelist = path[3].split(',')
            path_edgelist = list()
            for i in range(len(path_nodelist) - 1):
                path_edgelist.append((int(path_nodelist[i]), int(path_nodelist[i + 1]), 0))
            path_graph = system_graph.edge_subgraph(path_edgelist)
            draw_network_tofile(system_graph, path_graph, 0.3, foldername + '/' + str(path[0]) + '.pdf')

            path_node_details = list()
            for node in path_nodelist:
                database.execute('''SELECT Station.name, Route.type, Route.ref
                                    FROM Station JOIN Route ON Station.route_id = Route.id
                                    WHERE Route.system_id = ? AND Station.id = ? LIMIT 1''',
                                 (system_id, int(node)))
                path_node_details.append(database.fetchone())

            file.write('\n')
            file.write('Path ID: ' + str(path[0]) + ', from ' + str(path_node_details[0][0]) + ' (' +
                       str(path_node_details[0][1]) +
                       ', ' + str(path_node_details[0][2]) + ') to ' + str(path_node_details[-1][0]) +
                       ' (' + str(path_node_details[-1][1]) + ', ' + str(path_node_details[-1][2]) + ')\n')
            file.write('Path direct distance: ' + str(round(path[1], 2)) + ' km, path optimality: ' +
                       str(round(path[2], 2)) + '\n\n')
            file.write('STEPS: ' + str(path_node_details[0][0]) + ' (' + str(path_node_details[0][1]) +
                       ', ' + str(path_node_details[0][2]) + ')')

            current_node = 1
            for edge in path_edgelist:
                try:
                    edge_type = routes_type[(edge[0], edge[1], 0)]
                    edge_weight = distances[(edge[0], edge[1], 0)]
                except KeyError:
                    edge_type = routes_type[(edge[1], edge[0], 0)]
                    edge_weight = distances[(edge[1], edge[0], 0)]

                if edge_type != 'interchange':
                    file.write(' <-[' + edge_type + ', ' + str(round(edge_weight, 2)) + ' km]-> ')
                else:
                    file.write(' <-[' + edge_type + ']-> ')

                file.write(
                    str(path_node_details[current_node][0]) + ' (' + str(path_node_details[current_node][1]) +
                    ', ' + str(path_node_details[current_node][2]) + ')')
                current_node += 1

            file.write('\n\n')
            file.write('=================================' + '\n')


    else:
        with open(foldername + '/result.csv', 'a+', encoding='utf8') as file:
            file.write(str(path[0]) + '\n')
            file.write(str(path[3]) + '\n')

    return True


db_connection = sqlite3.connect('systems.sqlite')
database = db_connection.cursor()

city_name = input('Enter city to do paths\' analysis: ')
output_type = input('Select output type - Full (F) - gives full info and generates PDFs of each route, but can be '
                    'slow! / Short (S) - only path IDs and steps to csv: ')

if output_type.upper() != 'F':
    output_type = 'S'

system_graph = nx.read_gpickle('final/' + city_name + '.gpickle')

system_id = None

for node in system_graph.nodes():
    database.execute('''SELECT RailwaySystem.id FROM Station JOIN Route JOIN RailwaySystem
                        ON Station.route_id = Route.id AND Route.system_id = RailwaySystem.id
                        WHERE Station.id = ? LIMIT 1''', (node,))
    system_id = database.fetchone()[0]
    break

if system_id is None:
    print('Something went wrong, could not get system id based on graph from DB...')
    exit()

direct_distance_bottom_limit = float(input('Enter MIN direct distance in km (> than 1.5): '))
direct_distance_upper_limit = float(input('Enter MAX direct distance in km: '))

if direct_distance_upper_limit - direct_distance_bottom_limit < 0:
    print('Error, MIN direct distance cannot be more than MAX!')
    exit()

optimality_bottom_limit = float(input('Enter MIN optimality in range 0 to 1: '))
optimality_upper_limit = float(input('Enter MAX optimality in range 0 to 1: '))

if optimality_upper_limit - optimality_bottom_limit < 0:
    print('Error, MIN optimality cannot be more than MAX!')
    exit()

optimality_step = float(
    input('Enter size of step over optimality gradual increase (in range 0 to 1, default = 0.02): '))

if optimality_step <= 0:
    print('Error, step cannot be <= 0')
    exit()

datetime = datetime.now()
timestamp = datetime.strftime('%d-%b-%Y_%H:%M:%S')

foldername = 'paths_requests/' + city_name + '_' + timestamp + '_output_type=' + output_type.upper() + '_distrange(' + \
             str(direct_distance_bottom_limit) + ',' + \
             str(direct_distance_upper_limit) + ')_optrange(' + str(optimality_bottom_limit) + ',' + \
             str(optimality_upper_limit) + ')_optstep(' + str(optimality_step) + ')'

try:
    os.mkdir(foldername)
except OSError:
    print('Creation of the directory' + foldername + 'failed')

steps = round((optimality_upper_limit - optimality_bottom_limit) / optimality_step)
i = 0

optimality_current_limit = optimality_bottom_limit

print('Generating result.txt and PDFs of routes, may be slow...')

while optimality_current_limit < optimality_upper_limit:
    optimality_current_limit += optimality_step
    get_paths(output_type, direct_distance_bottom_limit, direct_distance_upper_limit, optimality_bottom_limit,
              optimality_current_limit, system_graph, database, foldername)
    optimality_bottom_limit += optimality_step
    i += 1
    print('Progress = '+ str(round((i / steps) * 100, 2)) + '%')


if output_type.upper() == 'F':
    print('result.txt and all PDFs successfully generated!')
else:
    print('result.csv successfully generated!')

db_connection.close()
# gui to create and unify all functions
# gpickle name with country to avoid same cities
# population density в точке...
# константы переменные
# комментарии к коду
