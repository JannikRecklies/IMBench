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

def assign_edge_weights_old(graph, alpha=1, lognorm_mu=0, lognorm_sigma=0.5, random_ratio=0.05):
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

def assign_edge_weights_powerlaw(graph, alpha=2.5, min_weight=0.01, max_weight=0.99):
    """
    Assigns edge weights drawn from a power-law distribution.

    Parameters:
        graph (networkx.Graph): Graph to assign edge weights to.
        alpha (float): Alpha for the power-law distribution (typical values between 2 and 3).
        min_weight (float): Minimum possible weight after scaling.
        max_weight (float): Maximum possible weight after scaling.

    Returns:
        graph (networkx.Graph): Graph with updated edge weights.
        weights (list): List of assigned edge weights.
    """
    num_edges = graph.number_of_edges()

    # Draw samples from a power-law distribution
    raw_weights = np.random.pareto(alpha, num_edges)

    # Normalize raw weights to [min_weight, max_weight]
    raw_weights = raw_weights - raw_weights.min()  # shift so minimum is 0
    raw_weights = raw_weights / raw_weights.max()  # scale to [0, 1]
    normalized_weights = min_weight + raw_weights * (max_weight - min_weight)

    # Assign weights to edges
    for (edge, weight) in zip(graph.edges(), normalized_weights):
        u, v = edge
        graph[u][v]['weight'] = round(weight, 2)

    return graph, normalized_weights