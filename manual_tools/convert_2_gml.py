import networkx as nx

type_and_city = input('Enter [type/city] to convert to GML: ')
system_graph = nx.read_gpickle(type_and_city + '.gpickle')
nx.write_gml(system_graph, type_and_city + '.gml')
print('done')
