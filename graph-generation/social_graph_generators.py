import networkx as nx
import numpy as np
import matplotlib.pyplot as plt

def generate_ws_graph(size=250, k=6, p=0.1):
    """Generates a Watts-Strogatz small-world graph with high clustering and short path lengths."""
    G = nx.watts_strogatz_graph(size, k, p)
    print("✅ WS Graph Generation Completed")
    return G

def generate_ba_graph(size=250, m=2):
    """Generates a Barabási-Albert graph capturing heavy-tailed degree distribution."""
    G = nx.barabasi_albert_graph(size, m)
    print("✅ BA Graph Generation Completed")
    return G

def generate_hk_graph(n, m=3, p=0.5):
    """
    Generates a Holme-Kim graph, which is an extension of Barabási-Albert (BA) that improves clustering by adding triadic closure."""
    G = nx.powerlaw_cluster_graph(n, m, p)
    return G

def assign_edge_weights_random(graph):
    weights = []
    
    for u, v in graph.edges():
        weight = np.round(np.random.lognormal(mean=0, sigma=1), 2)
        weights.append(weight)
    
    # Normalize weights to range [0,1]
    min_weight = min(weights)
    max_weight = max(weights)
    normalized_weights = [(w - min_weight) / (max_weight - min_weight) for w in weights]

    # Assign normalized weights back to the graph
    for i, (u, v) in enumerate(graph.edges()):
        graph[u][v]['weight'] = np.round(normalized_weights[i], 4)  # Rounded to 4 decimal places
    
    return graph, normalized_weights

def assign_edge_weights(graph, alpha=1.0, beta=1.0):
    """Assigns edge weights based on common neighbors, adjusted for degree rarity."""

    weights = []

    # Compute degree distribution statistics
    degrees = [deg for _, deg in graph.degree()]
    avg_degree = np.mean(degrees)
    std_degree = np.std(degrees)  # Measure how much a degree deviates from avg

    # Compute max common neighbors for normalization
    max_common_neighbors = max((len(list(nx.common_neighbors(graph, u, v))) for u, v in graph.edges()), default=1)

    for u, v in graph.edges():
        # Step 1: Base weight from common neighbors
        mutual_neighbors = len(list(nx.common_neighbors(graph, u, v)))
        base_weight = (mutual_neighbors + 1) / (max_common_neighbors + 1)  # Normalize to [0,1]

        # Step 2: Compute node degree rarity effect
        avg_node_degree = (graph.degree[u] + graph.degree[v]) / 2  # Avg degree of two nodes

        # Compute how much this degree deviates from the expected distribution
        if std_degree > 0:
            degree_rarity = np.exp(-beta * ((avg_node_degree - avg_degree) / std_degree) ** 2)
        else:
            degree_rarity = 1  # No effect if degree variance is 0

        # Step 3: Combine effects
        weight = base_weight * degree_rarity
        weights.append(weight)

    # Normalize final weights to [0,1]
    min_weight = min(weights)
    max_weight = max(weights)
    normalized_weights = [(w - min_weight) / (max_weight - min_weight) for w in weights]

    # Assign weights back to graph
    for (u, v), weight in zip(graph.edges(), normalized_weights):
        graph[u][v]['weight'] = round(weight, 4)

    return graph, normalized_weights

def assign_edge_weights_common_neighbors(graph):
    """Assigns edge weights based on the number of common neighbors, preserving a heavy-tailed distribution."""
    weights = []

    # Compute max common neighbors for normalization
    max_common_neighbors = max(len(list(nx.common_neighbors(graph, u, v))) for u, v in graph.edges())

    for u, v in graph.edges():
        mutual_neighbors = len(list(nx.common_neighbors(graph, u, v)))

        # Linear scaling
        weight = (mutual_neighbors + 1) / (max_common_neighbors + 1)  # +1 to avoid zero division
        weights.append(weight)

    # Assign weights back to graph
    for (u, v), weight in zip(graph.edges(), weights):
        graph[u][v]['weight'] = round(weight, 4)

    return graph, weights

def assign_edge_weights_degree(graph, alpha=0.5, lognorm_mu=0.0, lognorm_sigma=1.0, random_freq="auto"):
    """
    Assigns edge weights using an inverse-degree power-law transformation 
    with optional random outliers. 

    Parameters:
        graph (networkx.Graph): The graph to assign edge weights.
        alpha (float): Controls the inverse-degree scaling effect.
        lognorm_mu (float): Mean of log-normal distribution for randomness.
        lognorm_sigma (float): Sigma of log-normal distribution for randomness.
        random_freq (int or "auto" or None): 
            - If an integer N, every Nth edge will be assigned a fully random weight.
            - If "auto" (default), random_freq is set to max_degree / 2.
            - If None, no fully random weights are assigned.

    Returns:
        graph (networkx.Graph): Graph with assigned edge weights.
        normalized_weights (list): List of normalized edge weights.
    """
    weights = []
    max_degree = max(dict(graph.degree).values(), default=1)  # Get highest node degree
    
    if random_freq == "auto":
        random_freq = int(max_degree / 2)  # Default to max_degree / 2 if not set
    elif random_freq is None:
        random_freq = float("inf")  # Disable random weight assignment

    for i, (u, v) in enumerate(graph.edges()):
        if (i + 1) % random_freq == 0:
            # Every `random_freq` edges, insert a fully random weight (unless disabled)
            weight = np.random.uniform(0.01, 0.99)  # Fully random weight in (0,1)
        else:
            # Base weight using inverse-degree scaling
            base_weight = (1 / (graph.degree[u] + graph.degree[v])) ** alpha

            # Introduce randomness with log-normal scaling
            random_factor = np.random.lognormal(mean=lognorm_mu, sigma=lognorm_sigma)

            # Compute final weight
            weight = base_weight * random_factor

        weights.append(weight)

    # Normalize weights to range [0,1]
    min_weight, max_weight = min(weights), max(weights)
    normalized_weights = [(w - min_weight) / (max_weight - min_weight) for w in weights]

    # Assign normalized weights back to the graph
    for (u, v), weight in zip(graph.edges(), normalized_weights):
        graph[u][v]['weight'] = round(weight, 2)

    return graph, normalized_weights

def assign_combined_edge_weights(graph, alpha=0.5, beta=0.5):
    """
    Assigns edge weights by combining common neighbors and degree-based approaches, ensuring a heavy-tailed distribution.
    
    Parameters:
    - graph: NetworkX graph
    - alpha: Weighting factor for the common neighbors contribution
    - beta: Weighting factor for the degree-based contribution

    Returns:
    - graph: NetworkX graph with assigned edge weights
    - weights: List of assigned edge weights
    """

    weights = []

    # Compute max degree product for normalization
    max_degree_product = max((graph.degree[u] * graph.degree[v] for u, v in graph.edges()), default=1)

    for u, v in graph.edges():
        # Common Neighbors Factor (Relative to Min Degree of Nodes)
        mutual_neighbors = len(list(nx.common_neighbors(graph, u, v)))
        min_degree = min(graph.degree[u], graph.degree[v])  # Normalize by the smaller node
        common_neighbors_factor = (mutual_neighbors + 1) / (min_degree + 1)  # Ensure [0,1] scaling

        # Degree Factor (Smooth Inverse Effect)
        degree_product = graph.degree[u] * graph.degree[v]
        degree_factor = (1 / (1 + degree_product)) ** beta  # Avoid extreme low values

        # Combine factors multiplicatively (power-law transformation)
        weight = (common_neighbors_factor ** alpha) * (degree_factor ** beta)

        weights.append(weight)

    # Normalize weights to range [0,1]
    min_weight = min(weights)
    max_weight = max(weights)
    normalized_weights = [(w - min_weight) / (max_weight - min_weight) for w in weights]

    # Assign normalized weights back to graph
    for (u, v), weight in zip(graph.edges(), normalized_weights):
        graph[u][v]['weight'] = round(weight, 4)

    return graph, normalized_weights