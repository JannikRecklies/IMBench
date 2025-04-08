from influxdb_client import InfluxDBClient
import pandas as pd
import matplotlib.pyplot as plt
import os

# ========== Configuration ==========
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "uZa-erdN8bdeXUFO5e08zq2EjkX3vyW5R-Vu9SdlEFS94mJOsWSDuktlGpyCZgZ2E3ix5mzS74cmqiJKPoEKmg==")
INFLUX_ORG = os.getenv("INFLUX_ORG", "imbench")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "imbench")
PLOT_DIR = "plots/performance"
os.makedirs(PLOT_DIR, exist_ok=True)

client = InfluxDBClient(
    url=INFLUX_URL, 
    token=INFLUX_TOKEN, 
    org=INFLUX_ORG, 
    timeout=30_000  # ⏱️ Timeout in milliseconds (30 seconds)
)
query_api = client.query_api()

# Define query
flux_query_latency = """
messages = from(bucket: "imbench")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "message")
  |> group(columns: ["_field"])
  |> aggregateWindow(every: 1m, fn: count, createEmpty: false)
  |> map(fn: (r) => ({ _time: r._time, _field: "avg_messages", _value: r._value }))

sent = from(bucket: "imbench")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "message" and r._field == "time_sent")
  |> keep(columns: ["_time", "_value", "msgId", "sender", "receiver"])
  |> rename(columns: {_value: "time_sent"})

received = from(bucket: "imbench")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "message" and r._field == "time_received")
  |> keep(columns: ["_value", "msgId", "sender", "receiver"])
  |> rename(columns: {_value: "time_received"})

latency = join(tables: {sent: sent, received: received}, on: ["msgId", "sender", "receiver"])
  |> map(fn: (r) => ({
      msgId: r.msgId,
      sender: r.sender,
      receiver: r.receiver,
      _value: float(v: r.time_received) - float(v: r.time_sent),
      _time: r._time
    }))
  |> keep(columns: ["_time", "_value"])
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
  |> map(fn: (r) => ({ _time: r._time, _field: "avg_latency", _value: r._value }))
  |> group(columns: ["_field"])

union(tables: [messages, latency])
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
"""

flux_query_cpu = """
messages = from(bucket: "imbench")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "message")
  |> group(columns: ["_field"])
  |> aggregateWindow(every: 1m, fn: count, createEmpty: false)  // Counts all messages per minute
  |> map(fn: (r) => ({ _time: r._time, _field: "avg_messages", _value: r._value }))

cpu = from(bucket: "imbench")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "server_cpu_usage")
  |> filter(fn: (r) => r._field == "cpu_percentage")
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
  |> map(fn: (r) => ({ _time: r._time, _field: "cpu_usage", _value: r._value }))

union(tables: [messages, cpu])
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
"""

def plot_latency_vs_messages():
    # Run the query
    tables = query_api.query_data_frame(flux_query_latency)

    # Concatenate in case multiple tables are returned
    df = pd.concat(tables) if isinstance(tables, list) else tables

    # Convert _time to datetime if not already
    df["_time"] = pd.to_datetime(df["_time"])

    # Extract both series from pivoted DataFrame
    latency_series = df[["avg_latency", "_time"]].dropna()
    messages_series = df[["avg_messages", "_time"]].dropna()

    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Plot avg_messages on left Y-axis
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Messages per Minute", color='green')
    ax1.plot(messages_series["_time"], messages_series["avg_messages"], label="Messages per Minute", color='green')
    ax1.tick_params(axis='y', labelcolor='green')

    # Twin axis for latency
    ax2 = ax1.twinx()
    ax2.set_ylabel("Average Latency (s)", color='blue')
    ax2.plot(latency_series["_time"], latency_series["avg_latency"], label="Avg Latency", color='blue')
    ax2.tick_params(axis='y', labelcolor='blue')

    plt.title("Latency vs Message Rate Over Time")
    fig.tight_layout()

    # Optional grid
    ax1.grid(True, linestyle="--", alpha=0.5)
    
    # Save plot
    path = os.path.join(PLOT_DIR, "latency_vs_messages.png")
    plt.savefig(path)
    print(f"✅ Saved: {path}")
    plt.close()
    
def plot_cpu_vs_messages():
    # Run the query
    tables = query_api.query_data_frame(flux_query_cpu)

    # Concatenate in case multiple tables are returned
    df = pd.concat(tables) if isinstance(tables, list) else tables

    # Convert _time to datetime
    df["_time"] = pd.to_datetime(df["_time"])

    # Filter down to rows where both values are present
    filtered_df = df[["_time", "cpu_usage", "avg_messages"]].dropna()

    # Plotting
    fig, ax1 = plt.subplots(figsize=(12, 6))

    ax1.set_xlabel("Time")
    ax1.set_ylabel("Messages per Minute", color='green')
    ax1.plot(filtered_df["_time"], filtered_df["avg_messages"], color='green', label="Messages per Minute")
    ax1.tick_params(axis='y', labelcolor='green')

    ax2 = ax1.twinx()
    ax2.set_ylabel("CPU Usage (%)", color='red')
    ax2.plot(filtered_df["_time"], filtered_df["cpu_usage"], color='red', label="CPU Usage (%)")
    ax2.tick_params(axis='y', labelcolor='red')

    plt.title("CPU Usage vs Message Rate Over Time")
    fig.tight_layout()
    ax1.grid(True, linestyle="--", alpha=0.5)

    path = os.path.join(PLOT_DIR, "cpu_vs_messages.png")
    plt.savefig(path)
    print(f"✅ Saved: {path}")
    plt.close()

if __name__ == "__main__":
    plot_latency_vs_messages()
    plot_cpu_vs_messages()