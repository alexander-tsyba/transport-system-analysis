import networkx as nx

type_and_city = input('Enter [type/city]: ')
system_graph = nx.read_gpickle(type_and_city + '.gpickle')
station_from = int(input('First node: '))
station_to = int(input('Second node: '))

print(nx.shortest_path(system_graph, station_from, station_to, None))
