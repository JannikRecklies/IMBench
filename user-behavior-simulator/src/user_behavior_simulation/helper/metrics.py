from influxdb_client import InfluxDBClient, Point
import time
from influxdb_client.client.write_api import SYNCHRONOUS
import os

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

def log_metric(metric_name, field_name, field_value, tags):
    # print(f'Storing metrics: ${metric_name} - {field_name}: {field_value} - {tags}')
    point = Point(metric_name).field(field_name, field_value)
    for key, val in tags.items():
        point = point.tag(key, str(val))
    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)

def log_conversation_duration(client_id, recipient, conversation_id, duration):
    log_metric("conversation", "duration", float(duration), {"participant_a": client_id, "participant_b": recipient, "conversation_id": conversation_id})

def log_inter_conversation_time(client_id, recipient, conversation_id, inter_conversation_time):
    log_metric("conversation", "inter_conversation_time", float(inter_conversation_time), {"participant_a": client_id, "participant_b": recipient, "conversation_id": conversation_id})

def log_number_of_messages(client_id, recipient, conversation_id, number_of_messages):
    log_metric("conversation", "number_of_messages", int(number_of_messages), {"participant_a": client_id, "participant_b": recipient, "conversation_id": conversation_id})

def log_response_time(client_id, recipient, conversation_id, response_time):
    log_metric("conversation", "response_time", float(response_time), {"participant_a": client_id, "participant_b": recipient, "conversation_id": conversation_id})