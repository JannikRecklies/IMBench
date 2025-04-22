import random
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

def assign_edge_weights(graph, alpha=1, lognorm_mu=0, lognorm_sigma=0.5, random_ratio=0.05):
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
    # Step 1: Compute initial (unnormalized) weights
    raw_weights = []
    for u, v in graph.edges():
        base_weight = (1 / (graph.degree[u] + graph.degree[v])) ** alpha
        randomness = np.random.lognormal(mean=lognorm_mu, sigma=lognorm_sigma)
        raw_weights.append(base_weight * randomness)

    # Step 2: Normalize weights to [0.01, 0.99]
    min_w, max_w = min(raw_weights), max(raw_weights)
    normalized_weights = [
        0.01 + (w - min_w) * (0.99 - 0.01) / (max_w - min_w)
        for w in raw_weights
    ]

    # Step 3: Inject fully random weights every `random_freq` edges
    for i, ((u, v), weight) in enumerate(zip(graph.edges(), normalized_weights)):
        if random.random() < random_ratio:
            weight = np.random.uniform(0.01, 0.99)
        graph[u][v]["weight"] = round(weight, 2)

    return graph, normalized_weights