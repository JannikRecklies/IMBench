import asyncio
from influxdb_client import Point
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from collections import deque

INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "uZa-erdN8bdeXUFO5e08zq2EjkX3vyW5R-Vu9SdlEFS94mJOsWSDuktlGpyCZgZ2E3ix5mzS74cmqiJKPoEKmg=="
INFLUX_ORG = "imbench"
INFLUX_BUCKET = "imbench"

class AsyncBatchWriter:
    def __init__(self, client: InfluxDBClientAsync, batch_size=50, flush_interval=5):
        self.client = client
        self.write_api = self.client.write_api()
        self.queue = deque()
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.lock = asyncio.Lock()
        self._task = None
        self._running = True

    async def start(self):
        self._task = asyncio.create_task(self._flush_loop())

    async def stop(self):
        self._running = False
        await self._flush()  # Flush remaining data
        if self._task:
            self._task.cancel()
        await self.client.__aexit__(None, None, None)

    async def write_point(self, point: Point):
        async with self.lock:
            self.queue.append(point)
            if len(self.queue) >= self.batch_size:
                await self._flush()

    async def _flush(self):
        if not self.queue:
            return
        async with self.lock:
            points = list(self.queue)
            self.queue.clear()
        try:
            await self.write_api.write(bucket=INFLUX_BUCKET, record=points)
        except Exception as e:
            print(f"❌ Error writing batch to InfluxDB: {e}")

    async def _flush_loop(self):
        while self._running:
            await asyncio.sleep(self.flush_interval)
            await self._flush()
