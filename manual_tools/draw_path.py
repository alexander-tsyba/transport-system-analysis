import sqlite3
from networkx import nx
from draw_graph import draw_network_tofile
import os

db_connection = sqlite3.connect(os.path.dirname(os.path.dirname(__file__)) + 'systems.sqlite')
database = db_connection.cursor()

path_id = input('Enter path id to plot over the respective graph: ')

database.execute('SELECT system_id, steps FROM Path WHERE id = ? LIMIT 1', (path_id,))
path = database.fetchone()

database.execute('SELECT id, name FROM RailwaySystem WHERE id = ? LIMIT 1', (path[0],))

system = database.fetchone()

system_graph = nx.read_gpickle('final/' + str(system[1].split(',')[0]) + '.gpickle')

path_nodelist = path[3].split(',')
path_edgelist = list()
for i in range(len(path_nodelist) - 1):
    path_edgelist.append((int(path_nodelist[i]), int(path_nodelist[i + 1]), 0))

path_graph = system_graph.edge_subgraph(path_edgelist)

draw_network_tofile(system_graph, path_graph, 0.3)

db_connection.close()
