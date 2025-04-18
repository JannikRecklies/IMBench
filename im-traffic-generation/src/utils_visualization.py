import os
import matplotlib.pyplot as plt
import numpy as np
import user_behavior_simulation.helper.utils as utils

PLOT_DIR = "plots/utils"
os.makedirs(PLOT_DIR, exist_ok=True)

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


def plot_inter_conversation_time():
    times = [utils.get_inter_conversation_time() for _ in range(10000)]
    plot_histogram(
        values=times,
        title="Heavy-Tailed Inter-Conversation Time Distribution",
        xlabel="Inter-Conversation Time (minutes)",
        filename="inter_conversation_time_distribution.png",
        bin_size=1
    )


def plot_bursty_consecutive_messages():
    delays = [utils.get_bursty_consecutive_messages() for _ in range(10000)]
    plot_histogram(
        values=delays,
        title="Bursty Messages Distribution (amount of messages per burst train)",
        xlabel="Messages in a burst block",
        filename="bursty_messages_distribution.png",
        bin_size=1
    )
    
def plot_bursty_consecutive_message_delay():
    delays = [utils.get_bursty_message_delay() * 60 for _ in range(10000)]
    plot_histogram(
        values=delays,
        title="Bursty Message Delay Distribution (within a block)",
        xlabel="Delay between messages in a burst block (seconds)",
        filename="bursty_message_delay_distribution.png",
        bin_size=1
    )

def plot_expected_messages_per_conversation():
    expected_messages = [utils.get_expected_number_of_messages_for_conversation() for _ in range(10000)]
    plot_histogram(
        values=expected_messages,
        title="Distribution of Expected Messages per Conversation",
        xlabel="Expected Number of Messages per Conversation",
        filename="messages_per_conversation.png",
        bin_size=2
    )

def plot_response_delay_sync():
    times = [utils.get_response_delay("sync") * 60 for _ in range(10000)]
    plot_histogram(
        values=times,
        title="Sync Response Time Distribution",
        xlabel="Response Delay (seconds)",
        filename=f"response_delay_sync.png",
        bin_size=5
    )

def plot_response_delay_async():
    times = [utils.get_response_delay("async") for _ in range(10000)]
    plot_histogram(
        values=times,
        title="Async Response Time Distribution",
        xlabel="Response Delay (minutes)",
        filename=f"response_delay_async.png",
        bin_size=1
    )

def plot_message_size():
    times = [utils.get_message_size() for _ in range(10000)]
    plot_histogram(
        values=times,
        title="Message Size Distribution",
        xlabel="Message Size (bytes)",
        filename=f"message_size.png",
        bin_size=10
    )

if __name__ == "__main__":
    plot_inter_conversation_time()
    plot_bursty_consecutive_messages()
    plot_bursty_consecutive_message_delay()
    plot_expected_messages_per_conversation()
    plot_response_delay_sync()
    plot_response_delay_async()
    plot_message_size()
