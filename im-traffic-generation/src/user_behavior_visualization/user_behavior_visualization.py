from influxdb_client import InfluxDBClient
import matplotlib.pyplot as plt
import numpy as np
import os

# ========== Configuration ==========
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "uZa-erdN8bdeXUFO5e08zq2EjkX3vyW5R-Vu9SdlEFS94mJOsWSDuktlGpyCZgZ2E3ix5mzS74cmqiJKPoEKmg=="
INFLUX_ORG = "imbench"
INFLUX_BUCKET = "imbench"
PLOT_DIR = "plots"
os.makedirs(PLOT_DIR, exist_ok=True)

# ========== InfluxDB Setup ==========
influx_client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)
query_api = influx_client.query_api()


# ========== Utility Function to Query Influx ==========
def query_influx(field: str):
    flux = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -24h)
      |> filter(fn: (r) => r._measurement == "conversation" and r._field == "{field}")
      |> keep(columns: ["_value"])
    '''
    tables = query_api.query(flux)
    return [float(record.get_value()) for table in tables for record in table.records]


# ========== Plotting Functions ==========
def plot_histogram(values, title, xlabel, filename, bin_size=5):
    plt.figure(figsize=(10, 6))
    bins = range(0, int(max(values)) + bin_size, bin_size)
    plt.hist(values, bins=bins, edgecolor='black', alpha=0.7)

    # Labels & Title
    plt.xlabel(xlabel)
    plt.ylabel("Number of Conversations")
    plt.title(title)

    # Optional: add count text on bars
    counts, edges = np.histogram(values, bins=bins)
    for i in range(len(counts)):
        plt.text(edges[i] + bin_size / 2, counts[i], str(counts[i]),
                 ha='center', va='bottom', fontsize=8)

    # Style & Save
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    path = os.path.join(PLOT_DIR, filename)
    plt.savefig(path)
    plt.close()
    print(f"✅ Saved: {path}")


# ========== Entry Point ==========
if __name__ == "__main__":
    # Plot Number of Messages
    num_msgs = query_influx("number_of_messages")
    if num_msgs:
        plot_histogram(
            num_msgs,
            title="Distribution of Messages per Conversation",
            xlabel="Number of Messages Exchanged",
            filename="messages_per_conversation.png",
            bin_size=5
        )

    # Plot Conversation Duration (in minutes)
    durations = query_influx("duration")
    if durations:
        plot_histogram(
            durations,
            title="Distribution of Conversation Duration",
            xlabel="Conversation Duration (minutes)",
            filename="conversation_duration.png",
            bin_size=1
        )