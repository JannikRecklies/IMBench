import docker
import time
import logging
import os
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS

logging.basicConfig(level=logging.INFO)

DOCKER_CONTAINER_NAME = "denim-server"

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "uZa-erdN8bdeXUFO5e08zq2EjkX3vyW5R-Vu9SdlEFS94mJOsWSDuktlGpyCZgZ2E3ix5mzS74cmqiJKPoEKmg==")
INFLUX_ORG = os.getenv("INFLUX_ORG", "imbench") 
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "imbench") 

influx_client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)
write_api = influx_client.write_api(SYNCHRONOUS)

def get_container_cpu():
    client = docker.from_env()
    container = client.containers.get(DOCKER_CONTAINER_NAME)
    stats = container.stats(stream=False)

    cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
    system_delta = stats["cpu_stats"]["system_cpu_usage"] - stats["precpu_stats"]["system_cpu_usage"]

    # Use safe get with default to avoid KeyError
    percpu = stats["cpu_stats"]["cpu_usage"].get("percpu_usage", [])
    cpu_count = len(percpu) if percpu else 1  # fallback to 1 CPU if data missing

    if system_delta > 0.0 and cpu_delta > 0.0:
        cpu_percentage = (cpu_delta / system_delta) * cpu_count * 100.0
        return round(cpu_percentage, 2)
    return 0.0

while True:
    try:
        cpu = get_container_cpu()
        logging.info(f"📈 Logging CPU usage: {cpu}%")
        point = Point("server_cpu_usage").field("cpu_percentage", cpu)
        write_api.write(bucket=INFLUX_BUCKET, record=point)
    except Exception as e:
        logging.error(f"❌ Error getting CPU usage: {e}")
    time.sleep(30)