from influxdb_client import InfluxDBClient, Point
import time
from influxdb_client.client.write_api import SYNCHRONOUS

influx_client = InfluxDBClient(
    url="http://localhost:8086",
    token="uZa-erdN8bdeXUFO5e08zq2EjkX3vyW5R-Vu9SdlEFS94mJOsWSDuktlGpyCZgZ2E3ix5mzS74cmqiJKPoEKmg==",
    org="imbench"
)
write_api = influx_client.write_api(SYNCHRONOUS)

def log_metric(metric_name, value, tags):
    print(f'Storing metrics: ${metric_name} - {value} - {tags}')
    point = Point(metric_name).field("value", value)
    for key, val in tags.items():
        point = point.tag(key, str(val))
    write_api.write(bucket="imbench", org="imbench", record=point)

def log_conversation_duration(client_id, recipient, conversation_id, duration):
    log_metric("conversation_duration", duration, {"participant_a": client_id, "participant_b": recipient, "conversation_id": conversation_id})

def log_inter_conversation_time(client_id, recipient, conversation_id):
    log_metric("inter_conversation_time", time.time(), {"participant_a": client_id, "participant_b": recipient, "conversation_id": conversation_id})