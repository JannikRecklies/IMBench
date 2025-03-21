import asyncio
import websockets
import json
import random
import time
from scipy.stats import powerlaw
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import uuid
import time

class Client:
    def __init__(self, client_id, connections, ws_uri):
        self.client_id = str(client_id)
        self.connections = connections  # List of (neighbor, weight)
        self.ws_uri = ws_uri
        self.websocket = None
        self.ongoing_conversations = {}  # Track ongoing conversations
        # InfluxDB connection
        self.influx_client = InfluxDBClient(
            url="http://localhost:8086",
            token="uZa-erdN8bdeXUFO5e08zq2EjkX3vyW5R-Vu9SdlEFS94mJOsWSDuktlGpyCZgZ2E3ix5mzS74cmqiJKPoEKmg==",
            org="imbench"
        )
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)

    def generate_conversation_id(self, receiver):
        """Generate a unique conversation ID based on sender, receiver, and timestamp."""
        timestamp = int(time.time() * 1000)  # Milliseconds
        return f"{self.client_id}_{receiver}_{timestamp}"

    def start_conversation(self, recipient):
        """Start a new conversation and return the conversation ID."""
        conv_id = self.generate_conversation_id(self.client_id, recipient)
        self.ongoing_conversations[conv_id] = {
            "start_time": time.time(),
            "last_message_time": time.time(),
            "duration": self.get_conversation_duration(),
            "recipient": recipient
        }
        return conv_id

    def end_conversation(self, conv_id):
        """End a conversation."""
        if conv_id in self.ongoing_conversations:
            duration = time.time() - self.ongoing_conversations[conv_id]["start_time"]
            self.log_conversation_duration(conv_id, duration)
            print(f"🛑 {self.client_id} ended conversation {conv_id}.")
            del self.ongoing_conversations[conv_id]

    def get_conversation_id(self, sender, receiver):
        """Retrieve the conversation ID if it exists, else create a new one."""
        # Check existing conversations
        for conv_id in self.ongoing_conversations.keys():
            if sender in conv_id and receiver in conv_id:
                return conv_id
    
    def log_metric(self, metric_name, value, tags):
        point = Point(metric_name).field("value", value)
        for key, val in tags.items():
            point = point.tag(key, str(val))
        self.write_api.write(bucket="imbench", org="imbench", record=point)

    def log_conversation_duration(self, recipient, duration):
        """Logs the duration of a conversation to InfluxDB."""
        tags = {"client_id": self.client_id, "recipient": recipient}
        self.log_metric("conversation_duration", duration, tags)

    def log_inter_conversation_time(self, recipient, inter_time):
        """Logs the inter-conversation time to InfluxDB."""
        tags = {"client_id": self.client_id, "recipient": recipient}
        self.log_metric("inter_conversation_time", inter_time, tags)
    
    async def connect(self):
        """Connects to the WebSocket server and registers the client."""
        self.websocket = await websockets.connect(self.ws_uri, ping_interval=None)
        await self.register()
        print(f"✅ Client {self.client_id} connected.")

    async def register(self):
        """Registers the client with the server."""
        await self.websocket.send(json.dumps({"command": "register", "clientId": str(self.client_id)}))

    async def listen_for_messages(self):
        """Listens for incoming messages and schedules responses."""
        async for message in self.websocket:
            data = json.loads(message)

            if data.get("event") == "message_received" and str(data["clientId"]) == str(self.client_id):
                sender = data["sender"]
                received_message = data["message_content"]
                json_received_message = json.loads(received_message)
                conversation_id = json_received_message.get("conversation_id")
                message_text = json_received_message.get("text")

                print(f"📩 {self.client_id} received from {sender} (Conv: {conversation_id}): {received_message}")

                # Handle conversation end acknowledgment
                if message_text == "END_CONVERSATION":
                    if conversation_id in self.ongoing_conversations:
                        duration = time.time() - self.ongoing_conversations[conversation_id]["start_time"]
                        print(f"🛑 {self.client_id} acknowledges conversation {conversation_id} end with {sender}.")
                        del self.ongoing_conversations[conversation_id]
                    continue

                # Check if conversation ID exists in memory, if not, add it
                if conversation_id not in self.ongoing_conversations:
                    print(f"🆕 New conversation {conversation_id} initiated by {sender}.")
                    self.ongoing_conversations[conversation_id] = {
                        "start_time": time.time(),
                        "last_message_time": time.time(),
                        "duration": self.get_conversation_duration(),
                        "recipient": sender
                    }

                # Check if the conversation has ended
                if self.has_conversation_ended(conversation_id):
                    duration = time.time() - self.ongoing_conversations[conversation_id]["start_time"]
                    self.log_conversation_duration(conversation_id, duration)
                    print(f"🛑 {self.client_id} is ending conversation {conversation_id} with {sender}.")
                    await self.send_message(sender, "END_CONVERSATION", conversation_id)
                    del self.ongoing_conversations[conversation_id]
                    continue

                self.ongoing_conversations[conversation_id]["last_message_time"] = time.time()

                # Respond to the message
                delay = self.get_response_delay()
                print(f"⏳ {self.client_id} will respond to {sender} in {delay:.2f}s")
                await asyncio.sleep(delay)
                await self.send_message(sender, f"Reply from {self.client_id}", conversation_id)

    async def send_message(self, recipient, text, conversation_id):
        """Sends a message to another client."""
        content = self.generate_message_content(conversation_id, text)
        await self.websocket.send(json.dumps({
            "command": "send",
            "clientId": str(self.client_id),
            "recipientId": str(recipient),
            "message_content": str(content)
        }))
        print(f"📤 {self.client_id} → {recipient}: {content}")
        
    
    async def simulate_behavior(self):
        """Randomly initiates conversations at different times."""
        while True:
            await asyncio.sleep(self.get_inter_conversation_time())  # Wait before attempting to initiate a chat
            if self.should_initiate_conversation():
                recipient = self.choose_recipient()
                # Check if there is already an ongoing conversation with this recipient
                ongoing = any(str(conv["recipient"]) == str(recipient) for conv in self.ongoing_conversations.values())
                if recipient and not ongoing:
                    # Generate a new conversation ID and store it in ongoing conversations
                    conversation_id = self.generate_conversation_id(recipient)
                    self.ongoing_conversations[conversation_id] = {
                        "recipient": str(recipient),
                        "start_time": time.time(),
                        "duration": self.get_conversation_duration()
                    }
                    print(f"📢 {self.client_id} initiates conversation {conversation_id} with {recipient}")
                    await self.send_message(recipient, "Hello!", conversation_id)

    async def run(self):
        """Main function that connects, listens, and simulates behavior."""
        await self.connect()
        asyncio.create_task(self.listen_for_messages())  # Background task
        asyncio.create_task(self.simulate_behavior())  # Background task
        await asyncio.Future()  # Keep the connection alive

    def choose_recipient(self):
        """Chooses a recipient based on connection weights."""
        if not self.connections:
            return None
        return random.choices(
            [neighbor for neighbor, _ in self.connections],
            weights=[weight for _, weight in self.connections],
            k=1
        )[0]

    def get_response_delay(self):
        """Calculates a probabilistic response delay."""
        return 10  # Avg response delay ~3s

    def get_conversation_duration(self):
        """Calculates a probabilistic conversation duration."""
        duration = powerlaw.rvs(3.7) * 240  # 4 minutes as the mode
        return max(30, duration)  # Minimum duration of 30 seconds

    def get_inter_conversation_time(self):
        """Calculates time between conversation initiations."""
        inter_time = powerlaw.rvs(1.5) * 60  # Avg inter-conversation time in seconds
        return max(5, inter_time)  # Minimum 5 seconds between conversations

    def should_initiate_conversation(self):
        """Decides probabilistically if the client should start a conversation."""
        return random.random() < 0.3  # 30% chance to start a chat

    def has_conversation_ended(self, recipient):
        """Checks whether the ongoing conversation with a recipient has ended."""
        conversation = self.ongoing_conversations.get(recipient)
        if conversation:
            elapsed_time = time.time() - conversation["start_time"]
            return elapsed_time > conversation["duration"]
        return True
    
    def generate_message_content(self, conversation_id, text = None):
        """Generates a message content with conversation ID and message ID."""
        message_id = str(uuid.uuid4())  # Generate a unique message ID
        if text is None:
            text = f"Message from {self.client_id} in conversation {conversation_id}"

        message_content = {
            "message_id": message_id,
            "conversation_id": str(conversation_id),
            "text": text
        }

        return json.dumps(message_content)
        