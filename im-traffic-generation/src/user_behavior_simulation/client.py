import asyncio
import websockets
import json
import random

class Client:
    def __init__(self, client_id, connections, ws_uri):
        self.client_id = str(client_id)
        self.connections = connections  # List of (neighbor, weight)
        self.ws_uri = ws_uri
        self.websocket = None

    async def connect(self):
        """Connects to the WebSocket server and registers the client."""
        self.websocket = await websockets.connect(self.ws_uri, ping_interval=None)
        await self.register()
        print(f"✅ Client {self.client_id} connected.")

    async def register(self):
        """Registers the client with the server."""
        await self.websocket.send(json.dumps({"command": "register", "clientId": str(self.client_id)}))
    
    async def send_message(self, recipient, text):
        """Sends a message to another client."""
        await self.websocket.send(json.dumps({
            "command": "send",
            "clientId": str(self.client_id),
            "recipientId": str(recipient),
            "text": str(text)
        }))
        print(f"📤 {self.client_id} → {recipient}: {text}")

    async def listen_for_messages(self):
        """Listens for incoming messages and schedules responses."""
        async for message in self.websocket:
            data = json.loads(message)

            if data.get("event") == "message_received" and str(data["clientId"]) == str(self.client_id):
                sender = data["sender"]
                received_message = data["message"]
                print(f"📩 {self.client_id} received from {sender}: {received_message}")

                if self.should_end_conversation():
                    print(f"🛑 {self.client_id} is ending conversation with {sender}.")
                    return  # Stop responding

                delay = self.get_response_delay()
                print(f"⏳ {self.client_id} will respond in {delay:.2f}s")
                await asyncio.sleep(delay)
                await self.send_message(sender, f"Reply from {self.client_id}")

    async def simulate_behavior(self):
        """Randomly initiates conversations at different times."""
        while True:
            await asyncio.sleep(random.uniform(5, 15))  # Random delay before initiating chat
            if self.should_initiate_conversation():
                recipient = self.choose_recipient()
                if recipient:
                    print(f"📢 {self.client_id} initiates conversation with {recipient}")
                    await self.send_message(recipient, "Hello!")

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
        return max(1, random.expovariate(1/3))  # Avg response delay ~3s

    def should_end_conversation(self):
        """Decides probabilistically if the conversation should end."""
        return random.random() < 0.1  # 10% chance to stop responding

    def should_initiate_conversation(self):
        """Decides probabilistically if the client should start a conversation."""
        return random.random() < 0.3  # 30% chance to start a chat