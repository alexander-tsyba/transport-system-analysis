import networkx as nx

type_and_city = input('Enter [type/city]: ')
system_graph = nx.read_gpickle(type_and_city + '.gpickle')
station_from = int(input('First node: '))
station_to = int(input('Second node: '))

while station_from != station_to:
    for n in system_graph.neighbors(station_from):
        print(station_from, 'neighbour is', n)
        decision = input('Select? ')
        if decision.upper() == 'Y':
            station_from = n
