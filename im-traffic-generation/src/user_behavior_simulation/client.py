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

    async def _connect(self):
        """Connect to the WebSocket server."""
        self.websocket = await websockets.connect(self.ws_uri, ping_interval=None)
        await self.websocket.send(json.dumps({"command": "register", "clientId": str(self.client_id)}))
        print(f"✅ Connected Client {self.client_id}.")

    async def _listen_for_messages(self):
        """Listen for incoming messages and schedule responses."""
        async for message in self.websocket:
            await self._handle_message(message)

    async def _handle_message(self, message):
        """Handle a received message."""
        data = json.loads(message)

        if not messaging.is_relevant_message(data, self.client_id):
            return

        sender, conversation_id, message_text = messaging.extract_message_info(data)
        print(f"📩 Received Message [{sender} -> {self.client_id}] [Conv: {conversation_id}] --- {message_text}")

        if conversation_id not in self.ongoing_conversations: # New conversation was started by other participent
            self.ongoing_conversations[conversation_id] = conversation.create_conversation_obj(sender)
        elif conversation.is_end_of_conversation_message(message_text, conversation_id, self.ongoing_conversations):
            print(f"🛑 Received Conversation End Message [{sender} -> {self.client_id}] --- Conv_id: {conversation_id}")
            del self.ongoing_conversations[conversation_id]
            return
        elif conversation.should_conversation_end(self.ongoing_conversations[conversation_id]):
            print(f"🛑 Sending Conversation End Message [{sender} -> {self.client_id}] --- Conv_id: {conversation_id}")
            await self._end_conversation(sender, conversation_id)
            return
        else: # Update conversation object
            self.ongoing_conversations[conversation_id]["last_message_time"] = time.time()
        
        await self._respond_to_message(sender, conversation_id)

    async def _send_message(self, recipient, text, conversation_id):
        """Send a message."""
        content = messaging.generate_message_content(conversation_id, text)
        await self.websocket.send(json.dumps({
            "command": "send",
            "clientId": str(self.client_id),
            "recipientId": str(recipient),
            "message_content": content
        }))
        print(f'📤 Sent Message [{self.client_id} -> {recipient}] --- Content: "{content}"')

    async def _simulate_behavior(self):
        """Randomly initiates conversations at different times."""
        while True:
            inter_conversation_time = utils.get_inter_conversation_time()
            await asyncio.sleep(inter_conversation_time)
            if utils.should_initiate_conversation():
                recipient = utils.choose_recipient(self.connections)
                if conversation.can_start_new_conversation(recipient, self.ongoing_conversations):
                    await self._initiate_conversation(recipient, inter_conversation_time)

    async def _end_conversation(self, sender, conversation_id):
        """End the conversation and log its duration."""
        duration = time.time() - self.ongoing_conversations[conversation_id]["start_time"]
        metrics.log_conversation_duration(self.client_id, sender, conversation_id, duration)
        await self._send_message(sender, "END_CONVERSATION", conversation_id)
        del self.ongoing_conversations[conversation_id]

    async def _respond_to_message(self, sender, conversation_id):
        """Respond to the received message."""
        delay = utils.get_response_delay()
        print(f"⏳ Responding to Message [{self.client_id} -> {sender}] --- Delay: {delay:.2f}s")
        await asyncio.sleep(delay)
        await self._send_message(sender, f"Reply from {self.client_id}", conversation_id)

    async def _initiate_conversation(self, recipient, inter_conversation_time):
        """Initiate a new conversation."""
        conversation_id = conversation.generate_conversation_id(self.client_id, recipient)
        self.ongoing_conversations[conversation_id] = conversation.create_conversation_obj(recipient)
        print(f"📢 Initiating conversation [{self.client_id} ->  {recipient}] --- Conv_id: {conversation_id}")
        metrics.log_inter_conversation_time(self.client_id, recipient, conversation_id, inter_conversation_time) 
        await self._send_message(recipient, "Hello!", conversation_id)

    async def run(self):
        """Run the client, connecting and listening for messages."""
        await self._connect()
        asyncio.create_task(self._listen_for_messages())
        asyncio.create_task(self._simulate_behavior())
        await asyncio.Future()