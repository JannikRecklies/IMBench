import asyncio
import os
import uuid
import websockets
import json
import time
import user_behavior_simulation.helper.messaging as messaging
import user_behavior_simulation.helper.conversation as conversation
import user_behavior_simulation.helper.metrics as metrics
import user_behavior_simulation.helper.utils as utils

INTER_CONVERSATION_TIME_MINIMUM = float(os.getenv("INTER_CONVERSATION_TIME_MINIMUM", 0.1))
INTER_CONVERSATION_TIME_MAXIMUM = float(os.getenv("INTER_CONVERSATION_TIME_MAXIMUM", 120))
INTER_CONVERSATION_TIME_EXPONENT = float(os.getenv("INTER_CONVERSATION_TIME_EXPONENT", 0.5))

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
        conversation_id = message_content.get("conversationId")
        message_burst_block_id = message_content.get("messageBurstBlockId")
        message_text = message_content.get("additionalText")
        

        # Check if the message is a start conversation message
        if conversation_id not in self.ongoing_conversations:
            conversation_type = message_content.get("conversationType") 
            expected_number_of_messages = message_content.get("expectedNumberOfMessages") 
            self.ongoing_conversations[conversation_id] = conversation.create_conversation_obj(sender, conversation_type, expected_number_of_messages)
            # print(f"🆕 Received start of new conversation [{sender} -> {self.client_id}] [Conv: {conversation_id}] (Type: {conversation_type}, expected_number_of_messages: {expected_number_of_messages}s)")
        
        # Update the conversation object
        self.ongoing_conversations[conversation_id]["last_message_time"] = time.time()
        self.ongoing_conversations[conversation_id]["messages_exchanged"] = int(self.ongoing_conversations[conversation_id]["messages_exchanged"]) + 1
        
        print(f'📩 Received Message [{sender} -> {self.client_id}] --- Conv: {conversation_id} --- Message number: {self.ongoing_conversations[conversation_id]["messages_exchanged"]}/{self.ongoing_conversations[conversation_id]["expected_number_of_messages"]}')
        
        if int(self.ongoing_conversations[conversation_id]["messages_exchanged"]) >= int(self.ongoing_conversations[conversation_id]["expected_number_of_messages"]):
            del self.ongoing_conversations[conversation_id] 
        else:
            last_id = str(self.ongoing_conversations[conversation_id].get("last_message_burst_block_id", "")).strip()
            incoming_id = str(message_burst_block_id).strip()
            if last_id != incoming_id:
                self.ongoing_conversations[conversation_id]["last_message_burst_block_id"] = incoming_id
                await self._respond_to_message(sender, conversation_id)
            else:
                print("Already responding to message from same burst block.")
                

    async def _respond_to_message(self, sender, conversation_id):
        """Respond to the received message."""
        conversation_obj = self.ongoing_conversations[conversation_id]
        conversation_type = conversation_obj["conversation_type"]
        expected_number_of_messages = conversation_obj["expected_number_of_messages"]
        delay = utils.get_response_delay() * 60 # min to sec
        print(f"⏳ Delay until next Message [{self.client_id} -> {sender}] --- Conv: {conversation_id} --- {delay:.2f}sec")
        metrics.log_response_time(self.client_id, sender, conversation_id, delay)
        await asyncio.sleep(delay)
        await self._send_message(sender, conversation_id, conversation_type, expected_number_of_messages)

    async def _send_message(self, recipient, conversation_id, conversation_type="sync", expected_number_of_messages=4):
        """Send a message."""
        message_burst_block_id = str(uuid.uuid4()) 
        message_burst_block_size = utils.get_bursty_consecutive_messages()
        for i in range(message_burst_block_size): 
            message_size = utils.get_message_size()
            message_text = messaging.generate_message_text(message_size)
            message_content = {
                "messageId": str(uuid.uuid4()),
                "messageBurstBlockId": message_burst_block_id,
                "conversationId": conversation_id,
                "conversationType": conversation_type,
                "expectedNumberOfMessages": expected_number_of_messages,
                "additionalText": message_text
            }
            websocket_transfer_obj = {
                "command": "send",
                "clientId": str(self.client_id),
                "recipientId": str(recipient),
                "message_content": json.dumps(message_content)
            }
            await self.websocket.send(json.dumps(websocket_transfer_obj))
            self.ongoing_conversations[conversation_id]["messages_exchanged"] = int(self.ongoing_conversations[conversation_id]["messages_exchanged"]) + 1
            print(f'📤 Sent Message [{self.client_id} -> {recipient}] --- Conv: {conversation_id} --- Message number: {self.ongoing_conversations[conversation_id]["messages_exchanged"]}/{self.ongoing_conversations[conversation_id]["expected_number_of_messages"]}')
            
            if int(self.ongoing_conversations[conversation_id]["messages_exchanged"]) >= int(self.ongoing_conversations[conversation_id]["expected_number_of_messages"]):
                self._end_conversation(recipient, conversation_id)
                print(f"🛑 Deleting conversation from memory [{recipient} -> {self.client_id}]")
                return
            
            message_burst_block_delay_min = utils.get_bursty_message_delay()
            message_burst_block_delay_sec = message_burst_block_delay_min * 60
            await asyncio.sleep(message_burst_block_delay_sec)

    async def _simulate_behavior(self):
        """Randomly initiates conversations at different times."""
        while True:
            inter_conversation_time = utils.get_inter_conversation_time()
            await asyncio.sleep(inter_conversation_time * 60) # min to sec
            recipient = utils.choose_recipient(self.connections)
            if conversation.can_start_new_conversation(recipient, self.ongoing_conversations):
                await self._initiate_conversation(recipient, inter_conversation_time)

    def _end_conversation(self, sender, conversation_id):
        """End the conversation and log its duration."""
        duration_sec = time.time() - self.ongoing_conversations[conversation_id]["start_time"]
        duration_min = duration_sec / 60.0
        metrics.log_conversation_duration(self.client_id, sender, conversation_id, duration_min)
        metrics.log_number_of_messages(self.client_id, sender, conversation_id, self.ongoing_conversations[conversation_id]["messages_exchanged"])
        print(f"🛑 Store metadata of conversation and delete it from memory [{sender} -> {self.client_id}] --- Conv: {self.ongoing_conversations[conversation_id]}")
        del self.ongoing_conversations[conversation_id]

    async def _initiate_conversation(self, recipient, inter_conversation_time):
        """Initiate a new conversation."""
        conversation_id = conversation.generate_conversation_id(self.client_id, recipient)
        expected_number_of_messages = utils.get_expected_number_of_messages_for_conversation()
        conversation_type = utils.get_conversation_type()
        
        self.ongoing_conversations[conversation_id] = conversation.create_conversation_obj(recipient, conversation_type, expected_number_of_messages)
        print(f"📢 Initiating conversation [{self.client_id} -> {recipient}] --- Conv: {self.ongoing_conversations[conversation_id]}")
        metrics.log_inter_conversation_time(self.client_id, recipient, conversation_id, inter_conversation_time)
    
        await self._send_message(recipient, conversation_id, conversation_type, expected_number_of_messages)

    async def run(self):
        """Run the client, connecting and listening for messages."""
        await self._connect()
        asyncio.create_task(self._listen_for_messages())
        asyncio.create_task(self._simulate_behavior())
        await asyncio.Future()