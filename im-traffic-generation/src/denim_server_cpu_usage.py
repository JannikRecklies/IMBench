import subprocess
import time
from influxdb_client import InfluxDBClient, Point, WriteOptions

DOCKER_CONTAINER_NAME = "denim_server"
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "<your-token>"
INFLUX_ORG = "imbench"
INFLUX_BUCKET = "imbench"

#client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
#write_api = client.write_api(write_options=WriteOptions(batch_size=10, flush_interval=10000))

def get_container_cpu():
    result = subprocess.check_output([
        "docker", "stats", "--no-stream", "--format", "{{.Name}} {{.CPUPerc}}", DOCKER_CONTAINER_NAME
    ]).decode()
    try:
        _, cpu_str = result.strip().split()
        return float(cpu_str.strip('%'))
    except Exception as e:
        print("Failed to parse docker stats:", e)
        return None

while True:
    cpu_usage = get_container_cpu()
    if cpu_usage is not None:
        #point = Point("server_cpu_usage").field("cpu_percentage", cpu_usage)
        #write_api.write(bucket=INFLUX_BUCKET, record=point)
        print(f"📈 Logged CPU: {cpu_usage:.2f}%")
    time.sleep(10)  # collect every 10 seconds