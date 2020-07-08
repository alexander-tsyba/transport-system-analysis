import matplotlib.pyplot as plt
import networkx as nx


def draw_network_tofile(system_graph, path_graph=None, alpha_level=1.0, filename='test.pdf'):
    pos = nx.get_node_attributes(system_graph, 'pos')

    subway_edges = list(filter(lambda edge: edge[2]['type'] == 'subway', system_graph.edges(data=True)))
    train_edges = list(filter(lambda edge: edge[2]['type'] == 'train', system_graph.edges(data=True)))
    light_rail_edges = list(filter(lambda edge: edge[2]['type'] == 'light_rail', system_graph.edges(data=True)))
    tram_edges = list(filter(lambda edge: edge[2]['type'] == 'tram', system_graph.edges(data=True)))
    bus_edges = list(filter(lambda edge: edge[2]['type'] == 'bus', system_graph.edges(data=True)))
    trolleybus_edges = list(filter(lambda edge: edge[2]['type'] == 'trolleybus', system_graph.edges(data=True)))
    interchange_edges = list(filter(lambda edge: edge[2]['type'] == 'interchange', system_graph.edges(data=True)))

    dpi = 100
    plt.figure(figsize=(2048 / dpi, 2048 / dpi), dpi=dpi)

    nx.draw_networkx_nodes(system_graph, pos, node_size=0)
    nx.draw_networkx_labels(system_graph, pos, font_size=2)
    nx.draw_networkx_edges(system_graph, pos, edgelist=interchange_edges, edge_color='orange', width=0.5, alpha=alpha_level)
    nx.draw_networkx_edges(system_graph, pos, edgelist=trolleybus_edges, edge_color='red', style='dotted', width=0.8, alpha=alpha_level)
    nx.draw_networkx_edges(system_graph, pos, edgelist=bus_edges, edge_color='red', style='dotted', width=0.8, alpha=alpha_level)
    nx.draw_networkx_edges(system_graph, pos, edgelist=tram_edges, edge_color='magenta', style='dotted', width=0.8, alpha=alpha_level)
    nx.draw_networkx_edges(system_graph, pos, edgelist=light_rail_edges, edge_color='cyan', style='dashed', alpha=alpha_level)
    nx.draw_networkx_edges(system_graph, pos, edgelist=train_edges, edge_color='blue', style='dashed', alpha=alpha_level)
    nx.draw_networkx_edges(system_graph, pos, edgelist=subway_edges, edge_color='black', alpha=alpha_level)

    if path_graph is not None:
        nx.draw_networkx_nodes(path_graph, pos, node_size=0)
        nx.draw_networkx_edges(path_graph, pos, edge_color='green', width=2)

    plt.box(False)
    plt.savefig(filename, bbox_inches='tight')
    plt.cla()
    plt.close()


def draw_network(system_graph, path_graph=None, alpha_level=1.0):
    print('Graph size:', len(system_graph.nodes()))
    pos = nx.get_node_attributes(system_graph, 'pos')

    subway_edges = list(filter(lambda edge: edge[2]['type'] == 'subway', system_graph.edges(data=True)))
    train_edges = list(filter(lambda edge: edge[2]['type'] == 'train', system_graph.edges(data=True)))
    light_rail_edges = list(filter(lambda edge: edge[2]['type'] == 'light_rail', system_graph.edges(data=True)))
    tram_edges = list(filter(lambda edge: edge[2]['type'] == 'tram', system_graph.edges(data=True)))
    bus_edges = list(filter(lambda edge: edge[2]['type'] == 'bus', system_graph.edges(data=True)))
    trolleybus_edges = list(filter(lambda edge: edge[2]['type'] == 'trolleybus', system_graph.edges(data=True)))
    interchange_edges = list(filter(lambda edge: edge[2]['type'] == 'interchange', system_graph.edges(data=True)))

    dpi = 100
    plt.figure(figsize=(2048 / dpi, 2048 / dpi), dpi=dpi)

    nx.draw_networkx_nodes(system_graph, pos, node_size=0)
    nx.draw_networkx_edges(system_graph, pos, edgelist=interchange_edges, edge_color='orange', width=0.5, alpha=alpha_level)
    nx.draw_networkx_edges(system_graph, pos, edgelist=trolleybus_edges, edge_color='red', style='dotted', width=0.8, alpha=alpha_level)
    nx.draw_networkx_edges(system_graph, pos, edgelist=bus_edges, edge_color='red', style='dotted', width=0.8, alpha=alpha_level)
    nx.draw_networkx_edges(system_graph, pos, edgelist=tram_edges, edge_color='magenta', style='dotted', width=0.8, alpha=alpha_level)
    nx.draw_networkx_edges(system_graph, pos, edgelist=light_rail_edges, edge_color='cyan', style='dashed', alpha=alpha_level)
    nx.draw_networkx_edges(system_graph, pos, edgelist=train_edges, edge_color='blue', style='dashed', alpha=alpha_level)
    nx.draw_networkx_edges(system_graph, pos, edgelist=subway_edges, edge_color='black', alpha=alpha_level)

    if path_graph is not None:
        nx.draw_networkx_nodes(path_graph, pos, node_size=0)
        nx.draw_networkx_edges(path_graph, pos, edge_color='green', width=2)

    plt.box(False)
    plt.show()
    plt.cla()
    plt.close()


if __name__ == "__main__":
    type_and_city = input('Enter [type/city] to plot graph: ')
    system_graph = nx.read_gpickle(type_and_city + '.gpickle')
    draw_network(system_graph)
    #draw_network_tofile(system_graph)
