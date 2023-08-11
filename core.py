import networkx as nx
from itertools import permutations


def calculate_delivery_time(graph, path):
    total_time = 0
    for i in range(len(path) - 1):
        print(path[i], path[i+1])
        if path[i+1] in graph[path[i]]:
            total_time += graph[path[i]][path[i+1]]['weight']
        else:
            total_time = float('inf')
    return total_time


def find_optimal_route(graph, start, end, weight_limit):
    shortest_route = None
    min_delivery_time = float('inf')

    for num_stops in range(2, len(graph.nodes) + 1):
        for subset in permutations(graph.nodes, num_stops):
            if subset[0] != start or subset[-1] != end:
                continue

            total_weight = sum(graph.nodes[node]['weight'] for node in subset)
            if total_weight > weight_limit:
                continue

            delivery_time = calculate_delivery_time(graph, subset)
            if delivery_time < min_delivery_time:
                min_delivery_time = delivery_time
                shortest_route = subset

    return '->'.join(shortest_route), min_delivery_time
