from collections import Counter
import os
import matplotlib.pyplot as plt
import numpy as np
import user_behavior_simulation.helper.utils as utils


def plot_inter_conversation_time():
    times = [utils.get_inter_conversation_time() for _ in range(10000)]

    avg_time = np.mean(times)
    median_time = np.median(times)
    min_time = min(times)
    max_time = max(times)

    # Plotting the histogram
    plt.figure(figsize=(8, 6))
    plt.hist(times, bins=100, density=True, alpha=0.7, color='blue')
    plt.xlabel("Inter-Conversation Time (minutes)")
    plt.ylabel("Probability Density")
    plt.title("Heavy-Tailed Inter-Conversation Time Distribution")

    # Statistics text box
    stats_text = f"Avg Time: {avg_time:.2f} min\nMedian Time: {median_time:.2f} min\nMin Time: {min_time:.2f} min\nMax Time: {max_time:.2f} min"
    props = dict(boxstyle='round', facecolor='lightgray', alpha=0.7)
    plt.gca().text(0.95, 0.95, stats_text, transform=plt.gca().transAxes,
                   fontsize=10, verticalalignment='top', horizontalalignment='right', bbox=props)

    plt.show()

def plot_conversation_duration():
    times = [utils.get_conversation_duration() for _ in range(10000)]
    conversation_type_threshold = utils.get_conversation_type_threshold()
    
    avg_time = np.mean(times)
    median_time = np.median(times)
    min_time = min(times)
    max_time = max(times)

    # Plotting the histogram
    plt.figure(figsize=(8, 6))
    plt.hist(times, bins=100, density=True, alpha=0.7, color='blue')
    plt.xlabel("Sync Conversation Duration (minutes)")
    plt.ylabel("Probability Density")
    plt.title("Heavy-Tailed Conversation Duration Distribution")

    # Statistics text box
    stats_text = f"Avg Time: {avg_time:.2f} min\nMedian Time: {median_time:.2f} min\nMin Time: {min_time:.2f} min\nMax Time: {max_time:.2f} min\nSync-Async-Threshold: {conversation_type_threshold:.2f} min"
    props = dict(boxstyle='round', facecolor='lightgray', alpha=0.7)
    plt.gca().text(0.95, 0.95, stats_text, transform=plt.gca().transAxes,
                   fontsize=10, verticalalignment='top', horizontalalignment='right', bbox=props)

    plt.show()

def plot_expected_messages_per_conversation():
    expected_messages = [utils.get_expected_number_of_messages_for_conversation() for _ in range(10000)]

    avg = np.mean(expected_messages)
    median = np.median(expected_messages)
    min_val = min(expected_messages)
    max_val = max(expected_messages)

    # Plotting the histogram
    plt.figure(figsize=(8, 6))
    plt.hist(expected_messages, bins=range(int(min_val), int(max_val) + 2), density=True, alpha=0.7, color='green')
    plt.xlabel("Expected Number of Messages per Conversation")
    plt.ylabel("Probability Density")
    plt.title("Distribution of Expected Messages per Conversation")

    # Statistics text box
    stats_text = f"Avg: {avg:.2f}\nMedian: {median:.2f}\nMin: {min_val:.0f}\nMax: {max_val:.0f}"
    props = dict(boxstyle='round', facecolor='lightgray', alpha=0.7)
    plt.gca().text(0.95, 0.95, stats_text, transform=plt.gca().transAxes,
                   fontsize=10, verticalalignment='top', horizontalalignment='right', bbox=props)

    plt.show()

def plot_conversation_type(sample_size=100):
    expected_number_of_messages = [utils.get_expected_number_of_messages_for_conversation() for _ in range(sample_size)]
    conversation_types = [utils.get_conversation_type(m) for m in expected_number_of_messages]
    conversation_type_threshold = utils.get_conversation_type_threshold()

    # Count how many of each type
    counts = Counter(conversation_types)
    sync_count = counts.get("sync", 0)
    async_count = counts.get("async", 0)

    print(f"✅ Sync: {sync_count} ({sync_count/sample_size*100:.2f}%)")
    print(f"✅ Async: {async_count} ({async_count/sample_size*100:.2f}%)")

    # Plotting
    plt.bar(["Sync", "Async"], [sync_count, async_count], color=["skyblue", "salmon"])
    plt.title(f"Distribution of Conversation Types - Threshold: {conversation_type_threshold:.2f} min")
    plt.ylabel("Count")
    plt.xlabel("Conversation Type")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.show()

def plot_response_delay(conversation_type):
    times = [utils.get_response_delay(conversation_type) for _ in range(10000)]
    avg, med, mi, ma = np.mean(times), np.median(times), min(times), max(times)

    plt.figure(figsize=(8, 5))
    plt.hist(times, bins=100, alpha=0.7, color="green", density=True)
    plt.title(f"{conversation_type.capitalize()} Response Time Distribution")
    plt.xlabel("Response Delay (minutes)")
    plt.ylabel("Probability Density")

    stats_text = f"Avg: {avg:.2f}min / {avg*60:.2f}s \nMedian: {med:.2f}min / {med*60:.2f}s \nMin: {mi:.2f}min / {mi*60:.2f}s \nMax: {ma:.2f}min / {ma*60:.2f}s "
    plt.gca().text(0.95, 0.95, stats_text, transform=plt.gca().transAxes,
                   fontsize=10, verticalalignment='top', horizontalalignment='right',
                   bbox=dict(boxstyle="round", facecolor="lightgray", alpha=0.7))

    plt.tight_layout()
    plt.show()

if __name__=="__main__":
    #plot_inter_conversation_time(min_time=INTER_CONVERSATION_TIME_MINIMUM, max_time=INTER_CONVERSATION_TIME_MAXIMUM, exponent=INTER_CONVERSATION_TIME_EXPONENT)
    # Only once:
    plot_expected_messages_per_conversation()
    
