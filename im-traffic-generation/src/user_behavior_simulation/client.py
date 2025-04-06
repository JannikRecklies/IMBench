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
import redis

REDIS_HOST = str(os.getenv("REDIS_HOST", "localhost"))
REDIS_PORT = str(os.getenv("REDIS_PORT", 6379))

class Client:
    def __init__(self, client_id, connections, ws_uri):
        self.client_id = str(client_id)
        self.connections = connections
        self.ws_uri = ws_uri
        self.redis_pub = None
        self.redis_sub = None
        self.pubsub = None
        self.loop = None  # Will be set in run()
        self.ongoing_conversations = {}

    async def _connect(self):
        # Initialize Redis publisher and subscriber
        self.redis_pub = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        self.redis_sub = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        self.pubsub = self.redis_sub.pubsub()

        # Register this client by publishing a message to TS
        self.redis_pub.publish("register-client", json.dumps({
            "command": "register",
            "clientId": self.client_id
        }))
        print(f"✅ Published registration to channel py:client:{self.client_id}")

        # Just subscribe, no need to await or yield
        self.pubsub.subscribe(**{f"ts:client:{self.client_id}": self._redis_handler})
        print(f"✅ Subscribed to channel ts:client:{self.client_id}")
        self.pubsub.run_in_thread(sleep_time=0.001)

    def _redis_handler(self, message):
        """Handles messages from Redis PubSub in a thread."""
        if message["type"] != "message":
            return
        try:
            payload = json.loads(message["data"])
            print(f"📩 Redis message for {self.client_id}: {payload}")
            asyncio.run_coroutine_threadsafe(self._handle_message(payload), self.loop)
        except Exception as e:
            print(f"❌ Error handling message for {self.client_id}: {e}")

    def send_to_ts(self, data: dict):
        self.redis_pub.publish(f"py:client:{self.client_id}", json.dumps(data))
        print(f"📤 Sent to TS [py:client:{self.client_id}] -> {data}")

    async def _handle_message(self, data: dict):
        """Handle a received message."""
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
            self.send_to_ts(websocket_transfer_obj)
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
        self.loop = asyncio.get_event_loop()
        await self._connect()
        asyncio.create_task(self._simulate_behavior())
        await asyncio.Future()  # Keeps it alive