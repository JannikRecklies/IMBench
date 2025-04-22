import requests
import time
from datetime import datetime
from user_behavior_visualization.performance_metrics_visualization import plot_performance
from user_behavior_visualization.user_behavior_visualization import plot_user_behavior

BASE_URL = "http://localhost:8000"  # Adjust port if needed
EXPERIMENT_DURATION_MINUTES = 120

def start_experiment(num_clients=50):
    response = requests.post(f"{BASE_URL}/start", json={"number_of_clients": num_clients})
    if response.status_code == 200:
        print("✅ Experiment started successfully.")
        return datetime.utcnow()  # Return current UTC timestamp
    else:
        print(f"❌ Failed to start experiment: {response.status_code} - {response.text}")
        return None

def stop_experiment():
    response = requests.post(f"{BASE_URL}/stop")
    if response.status_code == 200:
        print("🛑 Experiment stopped successfully.")
        return datetime.utcnow()
    else:
        print(f"❌ Failed to stop experiment: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    start_time = None
    end_time = None

    try:
        start_time = start_experiment(num_clients=100)
        print(f"⏳ Experiment running for {EXPERIMENT_DURATION_MINUTES} minutes...")
        time.sleep(EXPERIMENT_DURATION_MINUTES*60)
    except KeyboardInterrupt:
        print("\n⚠️ Experiment interrupted by user.")
    finally:
        end_time = stop_experiment()

        if start_time and end_time:
            print(f"📈 Generating plots from {start_time} to {end_time}... Duration: {EXPERIMENT_DURATION_MINUTES}min")
            plot_performance(EXPERIMENT_DURATION_MINUTES)
            plot_user_behavior(EXPERIMENT_DURATION_MINUTES)