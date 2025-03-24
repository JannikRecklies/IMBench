import asyncio
import uuid
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

        sender = data["sender"]
        received_message = data["message_content"]
        
        message_content = json.loads(received_message)
        command = message_content.get("command")
        conversation_id = message_content.get("conversationId")
        conversation_type = message_content.get("conversationType", "sync")  # Default to "sync" if not specified
        expected_duration = message_content.get("expectedDuration", 300)  # Default to 300 seconds if not specified
        message_text = message_content.get("additionalText")
        print(f"📩 Received Message [{sender} -> {self.client_id}] [Conv: {conversation_id}] --- {message_text}")

        # Check if the message is a start conversation message
        if conversation_id not in self.ongoing_conversations:
            print(f"🆕 Starting new conversation [{sender} -> {self.client_id}] [Conv: {conversation_id}] (Type: {conversation_type}, Duration: {expected_duration}s)")
            self.ongoing_conversations[conversation_id] = conversation.create_conversation_obj(sender, conversation_type, expected_duration)
        elif conversation.is_end_of_conversation_message(message_text, conversation_id, self.ongoing_conversations):
            print(f"🛑 Received Conversation End Message [{sender} -> {self.client_id}] --- Conv_id: {conversation_id}")
            del self.ongoing_conversations[conversation_id]
            return
        elif conversation.should_conversation_end(self.ongoing_conversations[conversation_id]):
            print(f"🛑 Sending Conversation End Message [{sender} -> {self.client_id}] --- Conv_id: {conversation_id}")
            await self._end_conversation(sender, conversation_id)
            return
        else: # Update the conversation object
            self.ongoing_conversations[conversation_id]["last_message_time"] = time.time()
        
        await self._respond_to_message(sender, conversation_id)

    async def _send_message(self, recipient, text, conversation_id, conversation_type="sync", expected_duration=300):
        """Send a message."""
        message_content = {
            "messageId": str(uuid.uuid4()),
            "conversationId": conversation_id,
            "conversationType": conversation_type,
            "expectedDuration": expected_duration,
            "additionalText": text
        }
        websocket_transfer_obj = {
            "command": "send",
            "clientId": str(self.client_id),
            "recipientId": str(recipient),
            "message_content": json.dumps(message_content)
        }
        await self.websocket.send(json.dumps(websocket_transfer_obj))
        print(f'📤 Sent Message [{self.client_id} -> {recipient}] --- Content: "{message_content}" (ConvType: {conversation_type}, Duration: {expected_duration}s)')

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
        conversation_obj = self.ongoing_conversations[conversation_id]
        conversation_type = conversation_obj["conversation_type"]
        duration =conversation_obj["duration"]
        await self._send_message(sender, f"Reply from {self.client_id}", conversation_id, conversation_type, duration)

    async def _initiate_conversation(self, recipient, inter_conversation_time):
        """Initiate a new conversation."""
        conversation_id = conversation.generate_conversation_id(self.client_id, recipient)
        conversation_type = "sync"  # You can change this to "async" depending on logic
        expected_duration = utils.get_conversation_duration()
        
        self.ongoing_conversations[conversation_id] = conversation.create_conversation_obj(recipient, conversation_type, expected_duration)
        print(f"📢 Initiating conversation [{self.client_id} -> {recipient}] --- Conv_id: {conversation_id} (Type: {conversation_type}, Duration: {expected_duration}s)")
        metrics.log_inter_conversation_time(self.client_id, recipient, conversation_id, inter_conversation_time)
        
        # Send a start conversation message with the structured format
        start_message = {
            "command": "start_conversation",
            "clientId": str(self.client_id),
            "recipientId": str(recipient),
            "conversationId": conversation_id,
            "conversationType": conversation_type,
            "expectedDuration": expected_duration
        }
        await self._send_message(recipient, json.dumps(start_message), conversation_id)

    async def run(self):
        """Run the client, connecting and listening for messages."""
        await self._connect()
        asyncio.create_task(self._listen_for_messages())
        asyncio.create_task(self._simulate_behavior())
        await asyncio.Future()