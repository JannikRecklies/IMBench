import asyncio
import websockets
import json
import time
import user_behavior_simulation.helper.messaging as messaging
import user_behavior_simulation.helper.conversation as conversation
import user_behavior_simulation.helper.metrics as metrics
import user_behavior_simulation.helper.utils as utils


class Client:
    def __init__(self, client_id, connections, ws_uri):
        self.client_id = str(client_id)
        self.connections = connections
        self.ws_uri = ws_uri
        self.websocket = None
        self.ongoing_conversations = {}

    async def connect(self):
        """Connect to the WebSocket server."""
        self.websocket = await websockets.connect(self.ws_uri, ping_interval=None)
        await self.register()
        print(f"✅ Client {self.client_id} connected.")

    async def register(self):
        """Register the client with the server."""
        await self.websocket.send(json.dumps({"command": "register", "clientId": str(self.client_id)}))

    async def listen_for_messages(self):
        """Listen for incoming messages and schedule responses."""
        async for message in self.websocket:
            await self.handle_message(message)

    async def handle_message(self, message):
        """Handle a received message."""
        data = json.loads(message)

        if not self.is_relevant_message(data):
            return

        sender, conversation_id, message_text = self.extract_message_info(data)
        print(f"📩 {self.client_id} received from {sender} (Conv: {conversation_id}): {message_text}")

        if self.is_end_of_conversation(message_text, conversation_id, sender):
            return

        self.update_conversation(sender, conversation_id)

        if conversation.has_conversation_ended(self.ongoing_conversations[conversation_id]):
            await self.end_conversation(sender, conversation_id)
            return

        await self.respond_to_message(sender, conversation_id)

    def is_relevant_message(self, data):
        """Check if the message is relevant to this client."""
        return data.get("event") == "message_received" and str(data["clientId"]) == str(self.client_id)

    def extract_message_info(self, data):
        """Extract sender, conversation ID, and message text from the data."""
        sender = data["sender"]
        received_message = data["message_content"]
        json_received_message = json.loads(received_message)
        conversation_id = json_received_message.get("conversation_id")
        message_text = json_received_message.get("text")
        return sender, conversation_id, message_text

    def is_end_of_conversation(self, message_text, conversation_id, sender):
        """Handle conversation end acknowledgment."""
        if message_text == "END_CONVERSATION" and conversation_id in self.ongoing_conversations:
            duration = time.time() - self.ongoing_conversations[conversation_id]["start_time"]
            print(f"🛑 {self.client_id} acknowledges conversation {conversation_id} end with {sender}.")
            del self.ongoing_conversations[conversation_id]
            return True
        return False

    def update_conversation(self, sender, conversation_id):
        """Update or create a new conversation entry."""
        if conversation_id not in self.ongoing_conversations:
            print(f"🆕 New conversation {conversation_id} initiated by {sender}.")
            self.ongoing_conversations[conversation_id] = conversation.create_conversation_obj(sender)
        self.ongoing_conversations[conversation_id]["last_message_time"] = time.time()

    async def end_conversation(self, sender, conversation_id):
        """End the conversation and log its duration."""
        duration = time.time() - self.ongoing_conversations[conversation_id]["start_time"]
        metrics.log_conversation_duration(self.client_id, sender, conversation_id, duration)
        print(f"🛑 {self.client_id} is ending conversation {conversation_id} with {sender}.")
        await self.send_message(sender, "END_CONVERSATION", conversation_id)
        del self.ongoing_conversations[conversation_id]

    async def respond_to_message(self, sender, conversation_id):
        """Respond to the received message."""
        delay = utils.get_response_delay()
        print(f"⏳ {self.client_id} will respond to {sender} in {delay:.2f}s")
        await asyncio.sleep(delay)
        await self.send_message(sender, f"Reply from {self.client_id}", conversation_id)

    async def send_message(self, recipient, text, conversation_id):
        """Send a message."""
        content = messaging.generate_message_content(conversation_id, text)
        await self.websocket.send(json.dumps({
            "command": "send",
            "clientId": str(self.client_id),
            "recipientId": str(recipient),
            "message_content": content
        }))
        print(f"📤 {self.client_id} → {recipient}: {content}")

    async def simulate_behavior(self):
        """Randomly initiates conversations at different times."""
        while True:
            await asyncio.sleep(utils.get_inter_conversation_time())
            if utils.should_initiate_conversation():
                recipient = utils.choose_recipient(self.connections)
                if self.can_start_new_conversation(recipient):
                    await self.initiate_conversation(recipient)

    def can_start_new_conversation(self, recipient):
        """Check if a new conversation can be started with the recipient."""
        ongoing = any(str(conv["recipient"]) == str(recipient) for conv in self.ongoing_conversations.values())
        return recipient and not ongoing

    async def initiate_conversation(self, recipient):
        """Initiate a new conversation."""
        conversation_id = conversation.generate_conversation_id(self.client_id, recipient)
        self.ongoing_conversations[conversation_id] = conversation.create_conversation_obj(recipient)
        print(f"📢 {self.client_id} initiates conversation {conversation_id} with {recipient}")
        await self.send_message(recipient, "Hello!", conversation_id)

    async def run(self):
        """Run the client, connecting and listening for messages."""
        await self.connect()
        asyncio.create_task(self.listen_for_messages())
        asyncio.create_task(self.simulate_behavior())
        await asyncio.Future()