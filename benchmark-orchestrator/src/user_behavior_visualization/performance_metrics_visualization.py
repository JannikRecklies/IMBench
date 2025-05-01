import math
from influxdb_client import InfluxDBClient
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta

# ========== Configuration ==========
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "uZa-erdN8bdeXUFO5e08zq2EjkX3vyW5R-Vu9SdlEFS94mJOsWSDuktlGpyCZgZ2E3ix5mzS74cmqiJKPoEKmg==")
INFLUX_ORG = os.getenv("INFLUX_ORG", "imbench")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "imbench")

client = InfluxDBClient(
    url=INFLUX_URL, 
    token=INFLUX_TOKEN, 
    org=INFLUX_ORG, 
    timeout=600_000  # ⏱️ Timeout in milliseconds (30 seconds)
)
query_api = client.query_api()

# Define query
def generate_latency_query(time_range="-1h", window: str = "5m"):
    return f"""
      messages = from(bucket: "imbench")
        |> range(start: {time_range})
        |> filter(fn: (r) => r._measurement == "message")
        |> group(columns: ["_field"])
        |> aggregateWindow(every: {window}, fn: count, createEmpty: false)
        |> map(fn: (r) => ({{
          _time: r._time,
          _field: "avg_messages",
          _value: r._value
        }}))

      sent = from(bucket: "imbench")
        |> range(start: {time_range})
        |> filter(fn: (r) => r._measurement == "message" and r._field == "time_sent")
        |> keep(columns: ["_time", "_value", "msgId", "sender", "receiver"])
        |> rename(columns: {{_value: "time_sent"}})

      received = from(bucket: "imbench")
        |> range(start: {time_range})
        |> filter(fn: (r) => r._measurement == "message" and r._field == "time_received")
        |> keep(columns: ["_value", "msgId", "sender", "receiver"])
        |> rename(columns: {{_value: "time_received"}})

      latency = join(tables: {{sent: sent, received: received}}, on: ["msgId", "sender", "receiver"])
        |> map(fn: (r) => ({{
            msgId: r.msgId,
            sender: r.sender,
            receiver: r.receiver,
            _value: float(v: r.time_received) - float(v: r.time_sent),
            _time: r._time
          }}))
        |> keep(columns: ["_time", "_value"])
        |> aggregateWindow(every: {window}, fn: mean, createEmpty: false)
        |> map(fn: (r) => ({{
          _time: r._time,
          _field: "avg_latency",
          _value: r._value
        }}))
        |> group(columns: ["_field"])

      union(tables: [messages, latency])
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      """

def generate_cpu_vs_message_query(time_range: str = "-1h", window: str = "5m") -> str:
    return f"""
      messages = from(bucket: "imbench")
        |> range(start: {time_range})
        |> filter(fn: (r) => r._measurement == "message")
        |> group(columns: ["_field"])
        |> aggregateWindow(every: {window}, fn: count, createEmpty: false)
        |> map(fn: (r) => ({{
          _time: r._time,
          _field: "avg_messages",
          _value: r._value
        }}))

      cpu = from(bucket: "imbench")
        |> range(start: {time_range})
        |> filter(fn: (r) => r._measurement == "server_cpu_usage")
        |> filter(fn: (r) => r._field == "cpu_percentage")
        |> aggregateWindow(every: {window}, fn: mean, createEmpty: false)
        |> map(fn: (r) => ({{
          _time: r._time,
          _field: "cpu_usage",
          _value: r._value
        }}))

      union(tables: [messages, cpu])
        |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
      """

def plot_latency_vs_messages(time_range: str, plot_dir: str, window= "5m"):
    # Run the query
    flux_query_latency = generate_latency_query(time_range=time_range, window=window)
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
    path = os.path.join(plot_dir, "latency_vs_messages.png")
    plt.savefig(path)
    print(f"✅ Saved: {path}")
    plt.close()
    
def plot_cpu_vs_messages(time_range: str, plot_dir: str, window="5m"):
    # Run the query
    flux_query_cpu = generate_cpu_vs_message_query(time_range=time_range, window=window)
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

    path = os.path.join(plot_dir, "cpu_vs_messages.png")
    plt.savefig(path)
    print(f"✅ Saved: {path}")
    plt.close()

def plot_performance_old(time_range_min: int, plot_dir: str):
  time_range_str = f"-{time_range_min}m"
  os.makedirs(plot_dir, exist_ok=True)
  
  window = math.ceil(time_range_min / 100)
  window_str = f"{window}m"
  
  plot_latency_vs_messages(time_range=time_range_str, plot_dir=plot_dir, window=window_str)
  plot_cpu_vs_messages(time_range=time_range_str, plot_dir=plot_dir, window=window_str)


####################################################################################################################

def generate_latency_query_custom_range(start: str, end: str, window: str = "1m") -> str:
    return f"""
      messages = from(bucket: "imbench")
        |> range(start: {start}, stop: {end})
        |> filter(fn: (r) => r._measurement == "message")
        |> group(columns: ["_field"])
        |> aggregateWindow(every: {window}, fn: count, createEmpty: false)
        |> map(fn: (r) => ({{
          _time: r._time,
          _field: "avg_messages",
          _value: r._value
        }}))

      sent = from(bucket: "imbench")
        |> range(start: {start}, stop: {end})
        |> filter(fn: (r) => r._measurement == "message" and r._field == "time_sent")
        |> keep(columns: ["_time", "_value", "msgId", "sender", "receiver"])
        |> rename(columns: {{_value: "time_sent"}})

      received = from(bucket: "imbench")
        |> range(start: {start}, stop: {end})
        |> filter(fn: (r) => r._measurement == "message" and r._field == "time_received")
        |> keep(columns: ["_value", "msgId", "sender", "receiver"])
        |> rename(columns: {{_value: "time_received"}})

      latency = join(tables: {{sent: sent, received: received}}, on: ["msgId", "sender", "receiver"])
        |> map(fn: (r) => ({{
            msgId: r.msgId,
            sender: r.sender,
            receiver: r.receiver,
            _value: float(v: r.time_received) - float(v: r.time_sent),
            _time: r._time
          }}))
        |> keep(columns: ["_time", "_value"])
        |> aggregateWindow(every: {window}, fn: mean, createEmpty: false)
        |> map(fn: (r) => ({{
          _time: r._time,
          _field: "avg_latency",
          _value: r._value
        }}))
        |> group(columns: ["_field"])

      union(tables: [messages, latency])
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      """


def generate_cpu_vs_message_query_custom_range(start: str, end: str, window: str = "1m") -> str:
    return f"""
      messages = from(bucket: "imbench")
        |> range(start: {start}, stop: {end})
        |> filter(fn: (r) => r._measurement == "message")
        |> group(columns: ["_field"])
        |> aggregateWindow(every: {window}, fn: count, createEmpty: false)
        |> map(fn: (r) => ({{
          _time: r._time,
          _field: "avg_messages",
          _value: r._value
        }}))

      cpu = from(bucket: "imbench")
        |> range(start: {start}, stop: {end})
        |> filter(fn: (r) => r._measurement == "server_cpu_usage")
        |> filter(fn: (r) => r._field == "cpu_percentage")
        |> aggregateWindow(every: {window}, fn: mean, createEmpty: false)
        |> map(fn: (r) => ({{
          _time: r._time,
          _field: "cpu_usage",
          _value: r._value
        }}))

      union(tables: [messages, cpu])
        |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
      """
      
def split_query_ranges(start_time: datetime, end_time: datetime, chunk_hours: int):
    """Splits a time range into smaller chunks."""
    ranges = []
    current_start = start_time
    while current_start < end_time:
        current_end = min(current_start + timedelta(hours=chunk_hours), end_time)
        ranges.append((current_start, current_end))
        current_start = current_end
    return ranges

def plot_latency_vs_messages_df(df: pd.DataFrame, plot_dir: str):
    df["_time"] = pd.to_datetime(df["_time"])

    latency_series = df[["avg_latency", "_time"]].dropna()
    messages_series = df[["avg_messages", "_time"]].dropna()

    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Messages per Minute", color='green')
    ax1.plot(messages_series["_time"], messages_series["avg_messages"], label="Messages per Minute", color='green')
    ax1.tick_params(axis='y', labelcolor='green')

    ax2 = ax1.twinx()
    ax2.set_ylabel("Average Latency (s)", color='blue')
    ax2.plot(latency_series["_time"], latency_series["avg_latency"], label="Avg Latency", color='blue')
    ax2.tick_params(axis='y', labelcolor='blue')

    plt.title("Latency vs Message Rate Over Time")
    fig.tight_layout()
    ax1.grid(True, linestyle="--", alpha=0.5)

    path = os.path.join(plot_dir, "latency_vs_messages.png")
    plt.savefig(path)
    print(f"✅ Saved: {path}")
    plt.close()


def plot_cpu_vs_messages_df(df: pd.DataFrame, plot_dir: str):
    df["_time"] = pd.to_datetime(df["_time"])

    filtered_df = df[["_time", "cpu_usage", "avg_messages"]].dropna()

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

    path = os.path.join(plot_dir, "cpu_vs_messages.png")
    plt.savefig(path)
    print(f"✅ Saved: {path}")
    plt.close()

def plot_performance(time_range_min: int, plot_dir: str, chunk_hours: int = 2):
    os.makedirs(plot_dir, exist_ok=True)

    end_time = datetime.utcnow().replace(second=0, microsecond=0)
    start_time = end_time - timedelta(minutes=time_range_min)

    # Split into smaller chunks
    ranges = split_query_ranges(start_time, end_time, chunk_hours=chunk_hours)

    window = math.ceil(time_range_min / 100)
    window_str = f"{window}m"
    
    latency_dfs = []
    cpu_dfs = []

    for start, end in ranges:
        # Convert to RFC3339 format
        start_str = start.isoformat("T") + "Z"
        end_str = end.isoformat("T") + "Z"
        print(f"Chunk querry: {start_str} -> {end_str}")

        latency_query = generate_latency_query_custom_range(start=start_str, end=end_str)
        cpu_query = generate_cpu_vs_message_query_custom_range(start=start_str, end=end_str)

        latency_table = query_api.query_data_frame(latency_query)
        cpu_table = query_api.query_data_frame(cpu_query)

        latency_df = pd.concat(latency_table) if isinstance(latency_table, list) else latency_table
        cpu_df = pd.concat(cpu_table) if isinstance(cpu_table, list) else cpu_table

        latency_dfs.append(latency_df)
        cpu_dfs.append(cpu_df)
        
        print(f"Chunk successfully querried: {start_str} -> {end_str}")

    # Merge all chunks
    full_latency_df = pd.concat(latency_dfs)
    full_cpu_df = pd.concat(cpu_dfs)
    
    # Sort by time
    full_latency_df["_time"] = pd.to_datetime(full_latency_df["_time"])
    full_latency_df = full_latency_df.sort_values("_time")

    full_cpu_df["_time"] = pd.to_datetime(full_cpu_df["_time"])
    full_cpu_df = full_cpu_df.sort_values("_time")

    # 🆕 Apply rolling 10-min average
    full_latency_df["avg_latency"] = full_latency_df["avg_latency"].rolling(window=10, min_periods=1).mean()
    full_latency_df["avg_messages"] = full_latency_df["avg_messages"].rolling(window=10, min_periods=1).mean()

    full_cpu_df["cpu_usage"] = full_cpu_df["cpu_usage"].rolling(window=10, min_periods=1).mean()
    full_cpu_df["avg_messages"] = full_cpu_df["avg_messages"].rolling(window=10, min_periods=1).mean()

    # Pass smoothed dataframes to plotters
    plot_latency_vs_messages_df(full_latency_df, plot_dir)
    plot_cpu_vs_messages_df(full_cpu_df, plot_dir)


time_range_main = 20*60
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
experiment_plot_dir = f"plots/performance"
#plot_performance(time_range_main, f"{experiment_plot_dir}")