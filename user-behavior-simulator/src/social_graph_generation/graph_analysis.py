import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import social_graph_generator
from collections import defaultdict
import scipy.stats as stats
import powerlaw
from statsmodels.nonparametric.smoothers_lowess import lowess

# Function to compute and return key graph statistics
def compute_graph_statistics(G):
    avg_clustering = nx.average_clustering(G)
    
    avg_path_length = nx.average_shortest_path_length(G)
    graph_diameter = nx.diameter(G)
    
    # Compute the 90th percentile effective diameter
    shortest_paths = dict(nx.all_pairs_shortest_path_length(G))
    path_lengths = []
    
    for source in shortest_paths:
        for target, length in shortest_paths[source].items():
            if source != target:  # Ignore self-loops
                path_lengths.append(length)
    
    effective_diameter_90 = np.percentile(path_lengths, 90)
    
    degree_distribution = [deg for _, deg in G.degree()]
    
    return {
        "clustering_coefficient": avg_clustering,
        "path_length": avg_path_length,
        "diameter": graph_diameter,
        "effective_diameter_90": effective_diameter_90,
        "degree_distribution": degree_distribution
    }

# Function to run experiments for a single graph type at different sizes

def experiment_graph_model():
    sizes = [400, 4000]
    results = {}

    print(f"\n🔍 Running Experiments for HK Graph...\n")

    for n in sizes:
        print(f"📊 Generating HK Graph with {n} Nodes...")

        G = social_graph_generator.generate_hk_graph(n)

        # Compute statistics
        stats = compute_graph_statistics(G)
        degree_distribution = stats["degree_distribution"]

        # Fit power-law to degree distribution
        fit = powerlaw.Fit(degree_distribution, discrete=True)
        alpha = fit.power_law.alpha
        xmin = fit.power_law.xmin

        results[n] = {
            "graph": G,
            "stats": stats,
            "degree_distribution": degree_distribution,
            "fit": fit,
            "alpha": alpha,
            "xmin": xmin
        }

    # PLOTTING
    fig, axes = plt.subplots(1, len(sizes), figsize=(6 * len(sizes), 6))
    axes = axes.flatten()

    for ax, (n, data) in zip(axes, results.items()):
        degree_distribution = data["degree_distribution"]
        fit = data["fit"]

        # Plot empirical PDF
        fit.plot_pdf(ax=ax, color="skyblue", label="Empirical Data", linewidth=2)
        fit.power_law.plot_pdf(ax=ax, color="red", linestyle="--", label=f"Power-Law Fit (α ≈ {data['alpha']:.2f})")

        ax.set_xlabel("Node Degree", fontsize=11)
        ax.set_ylabel("Probability Density", fontsize=11)
        ax.set_title(f"HK Graph ({n} Nodes)", fontsize=13, fontweight="bold")
        ax.grid(True, which="both", linestyle="dotted", alpha=0.7)
        ax.legend()

        # Add graph statistics as text
        stats_text = (
            f"Clustering: {data['stats']['clustering_coefficient']:.2f}\n"
            f"Avg. Shortest Path Length: {data['stats']['path_length']:.2f}\n"
            f"Diameter: {data['stats']['diameter']}"
        )
        ax.text(0.95, 0.95, stats_text, transform=ax.transAxes,
                fontsize=9, verticalalignment="top", horizontalalignment="right",
                bbox=dict(boxstyle="round,pad=0.4", edgecolor="black", facecolor="white", alpha=0.8))

    plt.tight_layout()
    plt.show()

def plot_weight_distribution(weights, num_bins=50):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Histogram of weights (linear scale)
    axes[0].hist(weights, bins=num_bins, color="b", edgecolor="black", alpha=0.7)
    axes[0].set_xlabel("Edge Weight", fontsize=10)
    axes[0].set_ylabel("Frequency", fontsize=10)
    axes[0].set_title("Edge Weight Distribution (Linear Scale)", fontsize=12, fontweight="bold")

    # Histogram of weights (log scale)
    axes[1].hist(weights, bins=num_bins, color="r", edgecolor="black", alpha=0.7)
    axes[1].set_yscale("log")
    axes[1].set_xlabel("Edge Weight", fontsize=10)
    axes[1].set_ylabel("Frequency (log scale)", fontsize=10)
    axes[1].set_title("Edge Weight Distribution (Log Scale)", fontsize=12, fontweight="bold")

    plt.tight_layout()
    plt.show()
        
def plot_avg_weight_vs_avg_degree(graph, num_bins=20):
    """Plots average edge weight vs. average node degree using equal-sized bins (same number of samples per bin)."""

    # Collect edge data
    degrees = []
    edge_weights = []

    for u, v, data in graph.edges(data=True):
        avg_degree = (graph.degree[u] + graph.degree[v]) / 2  # Avg degree of the two nodes
        degrees.append(avg_degree)
        edge_weights.append(data['weight'])

    # Sort data by degree
    sorted_indices = np.argsort(degrees)
    sorted_degrees = np.array(degrees)[sorted_indices]
    sorted_weights = np.array(edge_weights)[sorted_indices]

    # Divide data into bins with approximately equal number of points
    bin_size = len(degrees) // num_bins
    avg_degrees = []
    avg_weights = []

    for i in range(num_bins):
        start_idx = i * bin_size
        end_idx = start_idx + bin_size if i < num_bins - 1 else len(degrees)  # Ensure last bin gets remaining points

        bin_degrees = sorted_degrees[start_idx:end_idx]
        bin_weights = sorted_weights[start_idx:end_idx]

        avg_degrees.append(np.mean(bin_degrees))
        avg_weights.append(np.mean(bin_weights))

    # Plot results
    plt.figure(figsize=(8, 5))
    plt.plot(avg_degrees, avg_weights, linestyle="-", color="skyblue")
    plt.xlabel("Node Degree")
    plt.ylabel("Average Edge Weight")
    plt.title("Edge Weight vs. Node Degree")
    plt.grid(True, linestyle="dotted")
    plt.show()
    
def plot_avg_weight_vs_common_neighbors(graph):
    """Plots average edge weight vs. number of common neighbors, including frequency of edges per count."""
    
    # Dictionary to store all edge weights for each common neighbor count
    weight_dict = defaultdict(list)

    for u, v, data in graph.edges(data=True):
        mutual_count = len(list(nx.common_neighbors(graph, u, v)))
        weight_dict[mutual_count].append(data['weight'])

    # Compute averages and frequencies
    avg_neighbors = []
    avg_weights = []
    edge_counts = []  # Number of edges in each bin

    for neighbor_count in sorted(weight_dict.keys()):  # Ensure sorted order
        avg_neighbors.append(neighbor_count)
        avg_weights.append(np.mean(weight_dict[neighbor_count]))  # Average weight for this count
        edge_counts.append(len(weight_dict[neighbor_count]))  # Number of edges for this count

    # Create figure and axis
    fig, ax1 = plt.subplots(figsize=(8, 5))

    # Plot average edge weight (primary axis)
    ax1.plot(avg_neighbors, avg_weights, marker="o", linestyle="-", color="red", label="Avg. Edge Weight")
    ax1.set_xlabel("Number of Common Neighbors")
    ax1.set_ylabel("Average Edge Weight", color="red")
    ax1.tick_params(axis="y", labelcolor="red")

    # Create secondary y-axis for edge count
    ax2 = ax1.twinx()
    ax2.bar(avg_neighbors, edge_counts, alpha=0.4, color="blue", label="Edge Count")
    ax2.set_ylabel("Number of Edges", color="blue")
    ax2.set_yscale("log")
    ax2.tick_params(axis="y", labelcolor="blue")

    # Titles and grid
    plt.title("Avg. Edge Weight vs. Common Neighbors (with Edge Count)")
    ax1.grid(True, linestyle="dotted")

    # Show both legends
    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")

    plt.show()

def analyze_degree_common_neighbors_correlation(graph, num_bins=20):
    """Analyzes and visualizes the relationship between node degree and number of common neighbors."""
    
    degrees = []
    common_neighbors_counts = []

    for u, v in graph.edges():
        avg_degree = (graph.degree[u] + graph.degree[v]) / 2
        mutual_neighbors = len(list(nx.common_neighbors(graph, u, v)))

        degrees.append(avg_degree)
        common_neighbors_counts.append(mutual_neighbors)

    # Compute Pearson and Spearman Correlation
    pearson_corr, _ = stats.pearsonr(degrees, common_neighbors_counts)
    spearman_corr, _ = stats.spearmanr(degrees, common_neighbors_counts)
    
    print(f"📊 Pearson Correlation: {pearson_corr:.4f}")
    print(f"📊 Spearman Correlation: {spearman_corr:.4f}")

    # Binned Averages for Smoother Visualization
    sorted_indices = np.argsort(degrees)
    sorted_degrees = np.array(degrees)[sorted_indices]
    sorted_neighbors = np.array(common_neighbors_counts)[sorted_indices]

    bin_size = len(degrees) // num_bins
    avg_degrees = []
    avg_neighbors = []

    for i in range(num_bins):
        start_idx = i * bin_size
        end_idx = start_idx + bin_size if i < num_bins - 1 else len(degrees)

        bin_degrees = sorted_degrees[start_idx:end_idx]
        bin_neighbors = sorted_neighbors[start_idx:end_idx]

        avg_degrees.append(np.mean(bin_degrees))
        avg_neighbors.append(np.mean(bin_neighbors))

    # Plot Results
    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(avg_degrees, avg_neighbors, marker="o", linestyle="-", color="blue", label="Binned Avg.")
    ax.set_xscale("log")  
    ax.set_yscale("log")  
    ax.set_xlabel("Average Node Degree (log scale)")
    ax.set_ylabel("Average Common Neighbors (log scale)")
    ax.set_title("Correlation between node degree and common neighbors (Binned)")
    ax.grid(True, linestyle="dotted")

    plt.legend()
    plt.show()

def plot_weight_vs_degree(graph):
    """Plots edge weight vs. node degree as a scatter plot."""
    degrees = []
    edge_weights = []

    for u, v, data in graph.edges(data=True):
        avg_degree = (graph.degree[u] + graph.degree[v]) / 2  # Average degree of both nodes
        degrees.append(avg_degree)
        edge_weights.append(data['weight'])

    plt.figure(figsize=(8, 5))
    plt.scatter(degrees, edge_weights, alpha=0.5, s=10, color="skyblue")
    # plt.xscale("log")  # Log scale to better show heavy-tailed effects
    plt.xlabel("Average Node Degree between two connected Nodes")
    plt.ylabel("Edge Weight")
    plt.title("Edge Weight vs. Node Degree")
    plt.grid(True, linestyle="dotted")
    plt.show()

def plot_total_weight_vs_degree(graph):
    """Plots total edge weight per node vs. node degree to check cumulative weight distribution."""
    
    node_degrees = []
    total_weights = []

    for node in graph.nodes():
        degree = graph.degree[node]
        total_weight = sum(data['weight'] for _, _, data in graph.edges(node, data=True))
        
        node_degrees.append(degree)
        total_weights.append(total_weight)

    # Scatter plot
    plt.figure(figsize=(8, 5))
    plt.scatter(node_degrees, total_weights, alpha=0.5, s=10, color="green")
    plt.xscale("log")  # Log-scale to better see patterns
    plt.yscale("log")  # Log-scale to emphasize heavy-tailed effects
    plt.xlabel("Node Degree (log scale)")
    plt.ylabel("Total Node Strength (sum of edge weights, log scale)")
    plt.title("Total Edge Weight per Node vs. Node Degree")
    plt.grid(True, linestyle="dotted")
    plt.show()

def plot_weight_vs_degree_lowess(graph, filename: str, frac=0.1):
    degrees = []
    weights = []

    for u, v, attr in graph.edges(data=True):
        avg_deg = (graph.degree[u] + graph.degree[v]) / 2
        weight = attr.get("weight", 0)
        degrees.append(avg_deg)
        weights.append(weight)

    degrees = np.array(degrees)
    weights = np.array(weights)

    # Sort by degree for cleaner LOWESS curve
    sorted_idx = np.argsort(degrees)
    degrees = degrees[sorted_idx]
    weights = weights[sorted_idx]

    # Apply LOWESS smoothing
    smoothed = lowess(weights, degrees, frac=frac, return_sorted=True)

    # Plot
    plt.figure(figsize=(10, 6))
    plt.scatter(degrees, weights, alpha=0.4, s=10, color="skyblue", label="Individual Edges")
    plt.plot(smoothed[:, 0], smoothed[:, 1], color="blue", linewidth=2, label="Smoothed Degree–Weight Curve")

    plt.xlabel("Average Degree of Connected Node Pair")
    plt.ylabel("Edge Weight")
    plt.title("Edge Weight vs. Node Degree")
    plt.grid(True, linestyle="dotted", alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig(filename, dpi=200)
    plt.close()
    print(f"✅ Saved: {filename}")

def plot_weight_distribution_fit(weights: np.ndarray, filename: str, unit="weight", xmin=1.0):
    """
    Plots empirical edge weight distribution with fitted power-law and log-normal overlays.

    Args:
        weights (np.ndarray): Array of edge weights.
        filename (str): Path to save the output plot.
        unit (str): Label unit for logs and axes.
        xmin (float): Lower bound for fitting.
    """
    if not weights.any():
        print("⚠️ No data provided.")
        return

    print(f"Fitting distributions to {len(weights)} values ({unit})...")

    try:
        fit = powerlaw.Fit(weights, xmin=xmin, discrete=False)

        alpha = fit.power_law.alpha
        mu = fit.lognormal.mu
        sigma = fit.lognormal.sigma

        # Compare fits
        R, p = fit.distribution_compare('power_law', 'lognormal')
        print(f"📈 Power-law α: {alpha:.4f}")
        print(f"📉 Log-normal μ: {mu:.4f}, σ: {sigma:.4f}")
        print(f"📊 Log-likelihood R = {R:.3f}, p = {p:.3f}")

        if p < 0.05:
            better_fit = "Power-law" if R > 0 else "Log-normal"
            print(f"✅ Better fit: {better_fit}")
        else:
            print("⚖️ No statistically significant difference between fits.")

        # Plotting
        plt.figure(figsize=(8, 6))
        fit.plot_pdf(label="Empirical Data", color="skyblue")
        fit.power_law.plot_pdf(label=f"Power-law (α ≈ {alpha:.2f})", color="red", linestyle="--")
        #fit.lognormal.plot_pdf(label=f"Log-normal (μ ≈ {mu:.2f}, σ ≈ {sigma:.2f})", color="green", linestyle="-.")

        plt.xlabel("Edge Weight")
        plt.ylabel("Probability Density")
        plt.title("Edge Weight Distribution")
        plt.legend()
        plt.grid(True, which="both", linestyle="--", alpha=0.6)
        plt.tight_layout()

        plt.savefig(filename, dpi=200)
        plt.close()
        print(f"✅ Saved: {filename}")

    except Exception as e:
        print(f"❌ Failed to fit and plot distributions: {e}")
        
# Run the experiment
if __name__ == "__main__":
    # test graph properties
    # experiment_graph_model()  # Change to desired graph type
    
    # test weight distribution
    G = social_graph_generator.generate_hk_graph(4000)
    graph, weights = social_graph_generator.assign_edge_weights_powerlaw(G, alpha=2.5)
    #plot_weight_distribution(weights, num_bins=100)
    plot_weight_distribution_fit(
        weights=np.array(weights),
        filename="plots/edge_weight_distribution_fit.png",
        unit="edge weight",
        xmin=0.01  # you can adjust if needed
    )
    #plot_weight_vs_degree_lowess(G, filename="plots/edge_weight_vs_node_degree.png")
    # plot_weight_vs_degree(G)
    # plot_avg_weight_vs_common_neighbors(G)
    # plot_total_weight_vs_degree(G)