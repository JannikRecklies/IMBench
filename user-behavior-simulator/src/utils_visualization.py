import collections
import os
import matplotlib.pyplot as plt
import numpy as np
import user_behavior_simulation.helper.utils as utils
import powerlaw
from scipy.stats import lognorm

PLOT_DIR = "plots/utils"
os.makedirs(PLOT_DIR, exist_ok=True)

def plot_powerlaw_fit_linear(values: np.ndarray, title, xlabel, filename, unit="minutes", bins=50):
    if not values.any():
        print("⚠️ No data provided to plot_powerlaw_fit.")
        return

    print(f"Fitting power-law to {values.size} values ({unit})...")

    try:
        # Shift data so min is ~0 (required by scipy's powerlaw distribution)
        xmin = np.min(values)
        shifted = values - xmin + 1e-6  # add small epsilon to avoid zero

        # Fit using MLE (method of moments is worse here)
        alpha = 1 + len(shifted) / np.sum(np.log(shifted / np.min(shifted)))
        print(f"Estimated power-law α: {alpha:.4f} (xmin = {xmin:.2f})")

        # Histogram (normalized)
        plt.figure(figsize=(10, 6))
        counts, bin_edges, _ = plt.hist(values, bins=bins, density=True, alpha=0.5, color='skyblue', edgecolor='black', label="Data")

        # Smooth power-law curve
        x = np.linspace(min(values), max(values), 500)
        C = (alpha - 1) / (xmin ** (1 - alpha))  # Normalization constant
        pdf = C * (x ** -alpha)

        plt.plot(x, pdf, 'r--', label=f"Power-law Fit\nα ≈ {alpha:.2f}")

        # Labels and styling
        plt.xlabel(xlabel)
        plt.ylabel("Probability Density")
        plt.title(title)
        plt.legend()
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()

        print(f"✅ Saved: {filename}")

    except Exception as e:
        print(f"❌ Failed to fit and plot power-law: {e}")

def plot_lognormal_fit_linear(values: np.ndarray, title, xlabel, filename, unit="minutes", bins=50):
    if not values.any():
        print("⚠️ No data provided to plot_lognormal_fit.")
        return

    print(f"Fitting log-normal to {values.size} values ({unit})...")

    try:
        # Statistics
        avg = np.mean(values)
        median = np.median(values)
        min_val = min(values)
        max_val = max(values)
        #stats_text = f"Avg: {avg:.2f}\nMedian: {median:.2f}\nMin: {min_val:.2f}\nMax: {max_val:.2f}"
        stats_text = f"Avg: {avg:.2f}\nMedian: {median:.2f}"
        print(stats_text)
    
        # Estimate mu and sigma from log-transformed data
        log_values = np.log(values[values > 0])  # Filter out zeros
        mu = np.mean(log_values)
        sigma = np.std(log_values)

        print(f"Estimated log-normal μ: {mu:.4f}")
        print(f"Estimated log-normal σ: {sigma:.4f}")

        # Prepare figure
        plt.figure(figsize=(10, 6))

        # Histogram (normalized to form a PDF)
        counts, bin_edges, _ = plt.hist(values, bins=bins, density=True, alpha=0.5, color='skyblue', edgecolor='black', label="Data")

        # X values for smooth curve
        x = np.linspace(min(values), max(values), 500)
        pdf = lognorm.pdf(x, s=sigma, scale=np.exp(mu))

        # Plot the fitted log-normal PDF
        plt.plot(x, pdf, 'r--', label=f"Log-normal Fit\nμ ≈ {mu:.2f}, σ ≈ {sigma:.2f}")
        
        # Plot stats
        props = dict(boxstyle='round', facecolor='lightgray', alpha=0.7)
        plt.gca().text(0.95, 0.95, stats_text, transform=plt.gca().transAxes,
                   fontsize=10, verticalalignment='top', horizontalalignment='right', bbox=props)
        
        # Labels and title
        plt.xlabel(xlabel)
        plt.ylabel("Probability Density")
        plt.title(title)
        plt.legend()
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()

        print(f"✅ Saved: {filename}")

    except Exception as e:
        print(f"❌ Failed to fit and plot log-normal: {e}")
    
# ========== Plotting Functions ==========
def plot_histogram(values, title, xlabel, filename, bin_size=5):
    plt.figure(figsize=(10, 6))
    bins = range(0, int(max(values)) + bin_size, bin_size)
    plt.hist(values, bins=bins, edgecolor='black', alpha=0.7)

    # Statistics
    avg = np.mean(values)
    median = np.median(values)
    min_val = min(values)
    max_val = max(values)
    #stats_text = f"Avg: {avg:.2f}\nMedian: {median:.2f}\nMin: {min_val:.2f}\nMax: {max_val:.2f}"
    stats_text = f"Avg: {avg:.2f}\nMedian: {median:.2f}"

    # Labels & Title
    plt.xlabel(xlabel)
    plt.ylabel("Frequency of Occurrence")
    plt.title(title)

    # Count labels on bars
    #counts, edges = np.histogram(values, bins=bins)
    #for i in range(len(counts)):
    #    plt.text(edges[i] + bin_size / 2, counts[i], str(counts[i]),
    #             ha='center', va='bottom', fontsize=8)

    # Stats box
    props = dict(boxstyle='round', facecolor='lightgray', alpha=0.7)
    plt.gca().text(0.95, 0.95, stats_text, transform=plt.gca().transAxes,
                   fontsize=10, verticalalignment='top', horizontalalignment='right', bbox=props)

    # Style & Save
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    path = os.path.join(PLOT_DIR, filename)
    plt.savefig(path, dpi=200)
    plt.close()
    print(f"✅ Saved: {path}")

def plot_powerlaw_fit(values: np.ndarray, title, xlabel, filename, unit="minutes", xmin=None, xmax=None, discrete=False):
    """
    Fits and plots a power-law distribution on given values.
    
    Parameters:
        values (list of float): Data to fit (e.g., conversation durations)
        title (str): Plot title
        xlabel (str): X-axis label
        filename (str): Output filename (PNG)
        unit (str): Unit label used in logs and plot titles
    """
    if not values.any():
        print("⚠️ No data provided to plot_powerlaw_fit.")
        return

    print(f"Fitting power-law to {values.size} values ({unit})...")

    try:
        fit = powerlaw.Fit(values, xmin=xmin, xmax=xmax, discrete=discrete)
        alpha = fit.power_law.alpha
        xmin = fit.power_law.xmin

        print(f"Estimated power-law exponent (α): {alpha:.4f}")
        print(f"Estimated lower bound (xmin): {xmin:.2f}")
        
        # Plot
        plt.figure(figsize=(8, 6))
        fit.power_law.plot_pdf(label=f"Power-law Fit (α ≈ {alpha:.2f})", color="red", linestyle="--")
        plt.xlabel(xlabel)
        plt.ylabel("Probability Density")
        plt.title(title)
        plt.legend()
        plt.grid(True, which="both", linestyle="--", alpha=0.6)
        plt.tight_layout()
        
        plt.savefig(filename)
        plt.close()
        print(f"✅ Saved: {filename}")

    except Exception as e:
        print(f"❌ Failed to fit power-law: {e}")

def plot_lognormal_fit(values: np.ndarray, title, xlabel, filename, unit="minutes"):
    """
    Fits and plots a log-normal distribution on given values.

    Parameters:
        values (list of float): Data to fit (e.g., conversation durations)
        title (str): Plot title
        xlabel (str): X-axis label
        filename (str): Output filename (PNG)
        unit (str): Unit label used in logs and plot titles
    """
    if not values.any():
        print("⚠️ No data provided to plot_lognormal_fit.")
        return

    print(f"Fitting log-normal to {values.size} values ({unit})...")

    try:
        # Statistics
        avg = np.mean(values)
        median = np.median(values)
        min_val = min(values)
        max_val = max(values)
        stats_text = f"Avg: {avg:.2f}\nMedian: {median:.2f}"
        print(stats_text)
    
        fit = powerlaw.Fit(values, xmin=1.0)
        mu = fit.lognormal.mu
        sigma = fit.lognormal.sigma
        xmin = fit.lognormal.xmin

        print(f"Estimated log-normal μ: {mu:.4f}")
        print(f"Estimated log-normal σ: {sigma:.4f}")
        print(f"Estimated lower bound (xmin): {xmin:.2f}")

        # Plot
        plt.figure(figsize=(8, 6))
        fit.lognormal.plot_pdf(label=f"Log-normal Fit (μ ≈ {mu:.2f}, σ ≈ {sigma:.2f})", color="green", linestyle="--")
        props = dict(boxstyle='round', facecolor='lightgray', alpha=0.7)
        plt.gca().text(0.95, 0.95, stats_text, transform=plt.gca().transAxes,
                   fontsize=10, verticalalignment='top', horizontalalignment='right', bbox=props)
        plt.xlabel(xlabel)
        plt.ylabel("Probability Density")
        plt.title(title)
        plt.legend()
        plt.grid(True, which="both", linestyle="--", alpha=0.6)
        plt.tight_layout()

        plt.savefig(filename)
        plt.close()
        print(f"✅ Saved: {filename}")

    except Exception as e:
        print(f"❌ Failed to fit log-normal: {e}")
        
def plot_inter_conversation_time():
    times = [utils.get_inter_conversation_time() for _ in range(10000)]
    plot_powerlaw_fit_linear(
        values=np.array(times),
        title="Heavy-Tailed Inter-Conversation Time Distribution",
        xlabel="Inter-Conversation Time (minutes)",
        filename=f"{PLOT_DIR}/inter_conversation_time_distribution_curve.png",
        bins=50
    )
    plot_powerlaw_fit(
        values=np.array(times),
        title="Heavy-Tailed Inter-Conversation Time Distribution",
        xlabel="Inter-Conversation Time (minutes)",
        filename=f"{PLOT_DIR}/inter_conversation_time_distribution.png"
    )


def plot_bursty_consecutive_messages():
    delays = [utils.get_bursty_consecutive_messages() for _ in range(10000)]
    plot_powerlaw_fit_linear(
        values=np.array(delays),
        title="Bursty Messages Distribution (amount of messages per burst train)",
        xlabel="Messages in a burst block",
        filename=f"{PLOT_DIR}/bursty_messages_distribution_curve.png",
        bins=9
    )
    plot_powerlaw_fit(
        values=np.array(delays),
        title="Bursty Messages Distribution (amount of messages per burst train)",
        xlabel="Messages in a burst block",
        filename=f"{PLOT_DIR}/bursty_messages_distribution.png",
        xmin=1,
        xmax=9,
        discrete=True
    )
    
def plot_bursty_consecutive_message_delay():
    delays = [utils.get_bursty_message_delay() * 60 for _ in range(10000)]
    plot_powerlaw_fit_linear(
        values=np.array(delays),
        title="Bursty Message Delay Distribution (within a block)",
        xlabel="Delay between messages in a burst block (seconds)",
        filename=f"{PLOT_DIR}/bursty_message_delay_distribution_curve.png",
        bins=15
    )
    plot_powerlaw_fit(
        values=np.array(delays),
        title="Bursty Message Delay Distribution (within a block)",
        xlabel="Delay between messages in a burst block (seconds)",
        filename=f"{PLOT_DIR}/bursty_message_delay_distribution.png"
    )

def plot_expected_messages_per_conversation():
    expected_messages = [utils.get_expected_number_of_messages_for_conversation() for _ in range(10000)]
    plot_lognormal_fit_linear(
        values=np.array(expected_messages),
        title="Distribution of Expected Messages per Conversation",
        xlabel="Expected Number of Messages per Conversation",
        filename=f"{PLOT_DIR}/messages_per_conversation_curve.png",
        bins=50
    )
    plot_lognormal_fit(
        values=np.array(expected_messages),
        title="Distribution of Expected Messages per Conversation",
        xlabel="Expected Number of Messages per Conversation",
        filename=f"{PLOT_DIR}/messages_per_conversation.png"
    )

def plot_response_delay_sync():
    times = [utils.get_response_delay("sync") * 60 for _ in range(10000)]
    plot_lognormal_fit_linear(
        values=np.array(times),
        title="Sync Response Time Distribution",
        xlabel="Response Delay (seconds)",
        filename=f"{PLOT_DIR}/response_delay_sync_curve.png",
        bins=50
    )
    plot_lognormal_fit(
        values=np.array(times),
        title="Sync Response Time Distribution",
        xlabel="Response Delay (seconds)",
        filename=f"{PLOT_DIR}/response_delay_sync.png"
    )

def plot_response_delay_async():
    times = [utils.get_response_delay("async") for _ in range(10000)]
    plot_lognormal_fit_linear(
        values=np.array(times),
        title="Async Response Time Distribution",
        xlabel="Response Delay (minutes)",
        filename=f"{PLOT_DIR}/response_delay_async_curve.png",
        bins=50
    )
    plot_lognormal_fit(
        values=np.array(times),
        title="Async Response Time Distribution",
        xlabel="Response Delay (minutes)",
        filename=f"{PLOT_DIR}/response_delay_async.png"
    )

def plot_message_size():
    times = [utils.get_message_size() for _ in range(10000)]
    plot_lognormal_fit_linear(
        values=np.array(times),
        title="Message Size Distribution",
        xlabel="Message Size (bytes)",
        filename=f"{PLOT_DIR}/message_size_curve.png",
        bins=50
    )
    plot_lognormal_fit(
        values=np.array(times),
        title="Message Size Distribution",
        xlabel="Message Size (bytes)",
        filename=f"{PLOT_DIR}/message_size.png"
    )

if __name__ == "__main__":
    plot_inter_conversation_time()
    plot_bursty_consecutive_messages()
    plot_bursty_consecutive_message_delay()
    plot_expected_messages_per_conversation()
    plot_response_delay_sync()
    plot_response_delay_async()
    plot_message_size()
