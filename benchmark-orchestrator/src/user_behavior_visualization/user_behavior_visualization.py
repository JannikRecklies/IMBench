import collections
from influxdb_client import InfluxDBClient
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import powerlaw
from datetime import datetime

# ========== Configuration ==========
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "uZa-erdN8bdeXUFO5e08zq2EjkX3vyW5R-Vu9SdlEFS94mJOsWSDuktlGpyCZgZ2E3ix5mzS74cmqiJKPoEKmg==")
INFLUX_ORG = os.getenv("INFLUX_ORG", "imbench")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "imbench")

# ========== InfluxDB Setup ==========
influx_client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG,
    timeout=180_000  # ⏱️ Timeout in milliseconds (30 seconds)
)
query_api = influx_client.query_api()

# ========== Utility Function to Query Influx ==========
def query_influx(field: str, time_range: str):
    flux = f'''
        from(bucket: "{INFLUX_BUCKET}")
        |> range(start: {time_range})
        |> filter(fn: (r) => r._measurement == "conversation" and r._field == "{field}")
        |> keep(columns: ["_value"])
        '''
    tables = query_api.query(flux)
    return np.array([float(record.get_value()) for table in tables for record in table.records])

def query_inter_event_time(time_range: str):
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: {time_range})
      |> filter(fn: (r) =>
        r._measurement == "message" and
        (r._field == "time_sent" or r._field == "time_received"))
      |> keep(columns: ["_time", "_field", "_value", "sender", "receiver"])
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''

    print("Querying inter-event data...")
    result = query_api.query_data_frame(query)
    df = pd.concat(result) if isinstance(result, list) else result

    if df.empty or "_time" not in df.columns:
        print("⚠️ No inter-event data found.")
        exit()

    df["_time"] = pd.to_datetime(df["_time"])

    # Build event list: user + timestamp from sent and received
    sent_df = df[["sender", "_time"]].dropna().rename(columns={"sender": "user"})
    recv_df = df[["receiver", "_time"]].dropna().rename(columns={"receiver": "user"})

    # Combine and sort
    events = pd.concat([sent_df, recv_df]).sort_values(by=["user", "_time"])

    # Compute inter-event time per user
    events["inter_event_time_sec"] = events.groupby("user")["_time"].diff().dt.total_seconds()
    iet_values = events["inter_event_time_sec"].dropna()

    return iet_values.to_numpy()

def query_conversation_pairs(time_range: str):
    query = f'''
        from(bucket: "{INFLUX_BUCKET}")
        |> range(start: {time_range})
        |> filter(fn: (r) =>
            r._measurement == "conversation" and r._field == "duration")
        |> keep(columns: ["_time", "_field", "_value", "conversation_id", "participant_a", "participant_b"])
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''

    print("Querying conversation pairs...")
    result = query_api.query_data_frame(query)
    df = pd.concat(result) if isinstance(result, list) else result

    if df.empty:
        print("⚠️ No conversation data found.")
        exit()

    # Build sender-receiver key (sorted so that 14→48 and 48→14 count as the same pair)
    df["pair"] = df.apply(lambda row: tuple(sorted([str(row["participant_a"]), str(row["participant_b"])])), axis=1)

    # Count number of conversations per pair
    pair_counts = df["pair"].value_counts().values.tolist()
    print(f"Found {len(pair_counts)} unique user pairs.")

    # Example: pair_counts = [12, 7, 3, 1, 1, 1, 1, ...]

    return np.array(pair_counts)

# ========== Plotting Functions ==========
def plot_histogram(values: np.ndarray, title, xlabel, filename, bin_size=5):
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
    plt.savefig(filename)
    plt.close()
    print(f"✅ Saved: {filename}")

def plot_distribution_curve(values: np.ndarray, title, xlabel, filename, bin_size=5):
    plt.figure(figsize=(10, 6))

    # Compute histogram bins
    bins = range(0, int(max(values)) + bin_size, bin_size)
    counts, edges = np.histogram(values, bins=bins)

    # Get bin centers for line plot
    bin_centers = 0.5 * (edges[:-1] + edges[1:])

    # Plot line graph
    plt.plot(bin_centers, counts, linestyle='-', color='skyblue', label="Distribution")

    # Labels & Title
    plt.xlabel(xlabel)
    #plt.xscale("log")
    plt.ylabel("Number of Conversations")
    plt.title(title)

    # Optional: add count text
    #for i in range(len(counts)):
    #    plt.text(bin_centers[i], counts[i], str(counts[i]), ha='center', va='bottom', fontsize=8)

    # Style & Save
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    print(f"✅ Saved: {filename}")

def plot_powerlaw_fit(values: np.ndarray, title, xlabel, filename, unit="minutes"):
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
        fit = powerlaw.Fit(values, xmin=1.0)
        alpha = fit.power_law.alpha
        xmin = fit.power_law.xmin

        print(f"Estimated power-law exponent (α): {alpha:.4f}")
        print(f"Estimated lower bound (xmin): {xmin:.2f}")

        # Plot
        plt.figure(figsize=(8, 6))
        fit.plot_pdf(label="Empirical Data", color="skyblue")
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
        fit = powerlaw.Fit(values, xmin=1.0)
        mu = fit.lognormal.mu
        sigma = fit.lognormal.sigma
        xmin = fit.lognormal.xmin

        print(f"Estimated log-normal μ: {mu:.4f}")
        print(f"Estimated log-normal σ: {sigma:.4f}")
        print(f"Estimated lower bound (xmin): {xmin:.2f}")

        # Plot
        plt.figure(figsize=(8, 6))
        fit.plot_pdf(label="Empirical Data", color="skyblue")
        fit.lognormal.plot_pdf(label=f"Log-normal Fit (μ ≈ {mu:.2f}, σ ≈ {sigma:.2f})", color="green", linestyle="--")
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

def plot_empirical_pdf_continuous(values, bins=50):
    """
    Returns (x_vals, y_vals) for plotting the empirical PDF of continuous data.
    """
    counts, bin_edges = np.histogram(values, bins=bins, density=True)
    x_vals = 0.5 * (bin_edges[1:] + bin_edges[:-1])  # bin centers
    y_vals = counts
    return x_vals, y_vals

def plot_empirical_pdf_discrete(values):
    # Custom histogram for empirical PMF
    counts = collections.Counter(values)
    x_vals = sorted(counts.keys())
    y_vals = [counts[x] / len(values) for x in x_vals]
    return x_vals, y_vals

def plot_powerlaw_vs_lognormal(values: np.ndarray, title, xlabel, filename, unit="minutes", discrete_values=False):
    """
    Fits and plots both power-law and log-normal distributions on the same plot.

    Parameters:
        values (list of float): Data to fit (e.g., conversation durations or inter-event times)
        title (str): Plot title
        xlabel (str): X-axis label
        filename (str): Output filename (PNG)
        unit (str): Unit label used in logs and plot titles
    """
    import os
    import matplotlib.pyplot as plt
    import powerlaw

    if not values.any():
        print("⚠️ No data provided.")
        return

    print(f"Fitting distributions to {values.size} values ({unit})...")

    try:
        fit = powerlaw.Fit(values, xmin=1.0)

        # Extract power-law params
        alpha = fit.power_law.alpha
        alpha_xmin = fit.power_law.xmin
        print(f"Power-law α: {alpha:.4f}, xmin: {alpha_xmin}")

        # Extract log-normal params
        mu = fit.lognormal.mu
        sigma = fit.lognormal.sigma
        lognorm_xmin = fit.lognormal.xmin
        print(f"Log-normal μ: {mu:.4f}, σ: {sigma:.4f}, xmin: {lognorm_xmin}")

        R, p = fit.distribution_compare('power_law', 'lognormal')
        print("📊 Distribution Comparison")
        print(f"Log-likelihood ratio R: {R:.3f}, p-value: {p:.3f}")
        if p < 0.05:
            if R > 0:
                print("Power-law is a significantly better fit.")
            else:
                print("Log-normal is a significantly better fit.")
        else:
            print("⚖️ No statistically significant difference between the two fits.")
        
        # Plot
        plt.figure(figsize=(8, 6))
        if discrete_values:
            x_vals, y_vals = plot_empirical_pdf_discrete(values)
            plt.plot(x_vals, y_vals, '-', label="Empirical Data", color="skyblue")    
        else:
            fit.plot_pdf(label="Empirical Data", color="skyblue")
        #fit.power_law.plot_pdf(label=f"Power-law Fit (α ≈ {alpha:.2f})", color="red", linestyle="--")
        fit.lognormal.plot_pdf(label=f"Log-normal Fit (μ ≈ {mu:.2f}, σ ≈ {sigma:.2f})", color="green", linestyle="-.")
        plt.xlabel(xlabel)
        plt.ylabel("Probability Density")
        plt.title(title)
        plt.legend()
        plt.grid(True, which="both", linestyle="--", alpha=0.6)
        plt.tight_layout()

        plt.savefig(filename)
        plt.close()
        print(f"✅ Saved plot to: {filename}")

    except Exception as e:
        print(f"❌ Failed to fit distributions: {e}")
        
# ========== Entry Point ==========
def plot_user_behavior(time_range_min: int):
    time_range_str = f"-{time_range_min}m"
    
    # Plot Conversation Duration (in minutes)
    durations = query_influx("duration", time_range=time_range_str)
    if durations.any():
        plot_powerlaw_fit(
            durations,
            title="Power-Law Fit of Conversation Duration Distribution",
            xlabel="Conversation Duration (minutes)",
            filename="conversation_duration_powerlaw.png",
            unit="minutes"
        )
        plot_lognormal_fit(
            durations,
            title="LogNormal Fit of Conversation Duration Distribution",
            xlabel="Conversation Duration (minutes)",
            filename="conversation_duration_lognormal.png",
            unit="minutes"
        )
    
    # Plot Inter-Conversation Time (in minutes)
    durations = query_influx("inter_conversation_time", time_range=time_range_str)
    if durations.any():
        plot_powerlaw_fit(
            durations,
            title="Power-Law Fit of Inter-Conversation Times Distribution",
            xlabel="Inter-Conversation Time (minutes)",
            filename="inter_conversation_time_powerlaw.png",
            unit="minutes"
        )
        plot_lognormal_fit(
            durations,
            title="LogNormal Fit of Inter-Conversation Times Distribution",
            xlabel="Inter-Conversation Time (seconds)",
            filename="inter_conversation_time_lognormal.png",
            unit="seconds"
        )
    
    # Plot Inter-Event Times (in minutes)
    iet_values = query_inter_event_time(time_range=time_range_str)
    if iet_values.any():
        plot_powerlaw_fit(
            iet_values,
            title="Power-Law Fit of Inter-Event Times Distribution",
            xlabel="Inter-Event Times (seconds)",
            filename="inter_event_times_powerlaw.png",
            unit="seconds"
        )
        plot_lognormal_fit(
            iet_values,
            title="LogNormal Fit of Inter-Event Times Distribution",
            xlabel="Inter-Event Times (seconds)",
            filename="inter_event_times_lognormal.png",
            unit="seconds"
        )

def plot_user_behavior_v2(time_range_min: int, plot_dir: str):
    time_range_str = f"-{time_range_min}m"
    os.makedirs(plot_dir, exist_ok=True)
    
    # Plot Conversation Duration (in minutes)
    durations = query_influx("duration", time_range=time_range_str)
    if durations.any():
        plot_powerlaw_vs_lognormal(
            durations,
            title="Log-normal Fit: Conversation Duration Distribution",
            xlabel="Conversation Duration (minutes)",
            filename=f"{plot_dir}/conversation_duration_comparison.png",
            unit="minutes"
        )
        plot_distribution_curve(durations, "Conversation Duration Graph", "Conversation Duration (minutes)", f"{plot_dir}/conversation_duration_histogram.png", bin_size=5)
    
    # Plot Inter-Conversation Time (in minutes)
    durations = query_influx("inter_conversation_time", time_range=time_range_str)
    if durations.any():
        plot_powerlaw_vs_lognormal(
            durations,
            title="Log-normal Fit: Inter-Conversation Times Distribution",
            xlabel="Inter-Conversation Time (minutes)",
            filename=f"{plot_dir}/inter_conversation_time_comparison.png",
            unit="minutes"
        )
        plot_distribution_curve(durations, "Inter-Conversation Times Graph", "Inter-Conversation Times (seconds)", f"{plot_dir}/inter_conversation_time_histogram.png", bin_size=10)
    
    # Plot Conversation Pair Conversations (in numbers)
    pair_counts = query_conversation_pairs(time_range=time_range_str)
    if pair_counts.any():
        plot_powerlaw_vs_lognormal(
            pair_counts,
            title="Log-normal Fit: Conversations per User Pair",
            xlabel="Number of Conversations per Pair",
            filename=f"{plot_dir}/pair_conversation_count_comparison.png",
            unit="conversations",
            discrete_values=True
        )
        plot_distribution_curve(pair_counts, "Conversations per User Pair Graph", "Number of Conversations per Pair", f"{plot_dir}/pair_conversation_count_histogram.png", bin_size=1)
    
    # Plot Inter-Event Times (in minutes)
    iet_values = query_inter_event_time(time_range=time_range_str)
    if iet_values.any():
        plot_powerlaw_vs_lognormal(
            iet_values,
            title="Log-normal Fit: Inter-Event Times Distribution",
            xlabel="Inter-Event Times (seconds)",
            filename=f"{plot_dir}/inter_event_times_comparison.png",
            unit="seconds"
        )
        plot_distribution_curve(iet_values, "Inter-Event Times Graph", "Inter-Event Times (seconds)", f"{plot_dir}/inter_event_times_histogram.png", bin_size=5)
    

time_range_main = 60*168
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
experiment_plot_dir = f"plots"
plot_user_behavior_v2(time_range_main, f"{experiment_plot_dir}/behavior")