import networkx as nx
import numpy as np
import matplotlib.pyplot as plt

def generate_hk_graph(n, m=3, p=0.5):
    """
    Generates a Holme-Kim graph, which is an extension of Barabási-Albert (BA) that improves clustering by adding triadic closure.
    
    Parameters:
        n (int): the number of nodes
        m (int): the number of random edges to add for each new node

        p (float): Probability of adding a triangle after adding a random edge
    """
    G = nx.powerlaw_cluster_graph(n, m, p)
    return G

def assign_edge_weights(graph, alpha=1, lognorm_mu=0, lognorm_sigma=0.5, random_freq="auto"):
    """
    Assigns edge weights using an inverse-degree power-law transformation 
    with optional random outliers. 

    Parameters:
        graph (networkx.Graph): The graph to assign edge weights.
        alpha (float): Controls the inverse-degree scaling effect.
	        - If alpha is large, the weight drops off faster for high-degree nodes.
	        - If alpha is small, the effect is weaker (less punishment for high-degree nodes).
        lognorm_mu (float): Mean of log-normal distribution for randomness. It shifts the entire weight distribution up or down.
            - For smaller weights on average, set lognorm_mu < 0 (e.g., -1 or -2).
	        - For larger weights on average, set lognorm_mu > 0 (e.g., 1 or 2).
        lognorm_sigma (float): Sigma of log-normal distribution for randomness. It increases or decreases how much variation there is in edge weights.
            - For weights to be similar, set lognorm_sigma low (e.g., 0.5).
	        - For more variation (bigger outliers), set lognorm_sigma high (e.g., 1.5 or 2).
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

    # Normalize weights to range [0.01, 0.99]
    min_weight, max_weight = min(weights), max(weights)
    normalized_weights = [0.01 + (w - min_weight) * (0.99 - 0.01) / (max_weight - min_weight) for w in weights]
        
    # Assign normalized weights back to the graph
    for (u, v), weight in zip(graph.edges(), normalized_weights):
        graph[u][v]['weight'] = round(weight, 2)

    return graph, normalized_weights