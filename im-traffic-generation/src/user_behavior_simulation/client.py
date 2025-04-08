import asyncio
import logging
import os
from datetime import datetime
import uuid
import websockets
import json
import time
import user_behavior_simulation.helper.messaging as messaging
import user_behavior_simulation.helper.conversation as conversation
import user_behavior_simulation.helper.metrics as metrics
import user_behavior_simulation.helper.utils as utils
from aio_pika import connect_robust, Message, ExchangeType, IncomingMessage

log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, f"debug_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # Still shows logs in VSCode terminal
    ]
)


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
EXCHANGE_NAME = "imbench_exchange"

class Client:
    def __init__(self, client_id, connections, ws_uri):
        self.client_id = str(client_id)
        self.connections = connections
        self.ongoing_conversations = {}
        self.message_tasks = {}  # maps conversation_id → asyncio.Task
        self.last_conversation_start_timestamp = time.time()
        self.loop = None
        self.channel = None
        self.exchange = None
        self.queue = None

    async def _connect(self):
        # 1. Connect to RabbitMQ
        connection = await connect_robust(RABBITMQ_URL)
        self.channel = await connection.channel()
        # await self.channel.set_qos(prefetch_count=1)

        # 2. Declare an exchange (fanout, direct, topic, etc.)
        self.exchange = await self.channel.declare_exchange(EXCHANGE_NAME, ExchangeType.TOPIC)

        # 3. Declare a queue for this client
        self.queue = await self.channel.declare_queue(f"py_client_{self.client_id}", durable=True)
        await self.queue.bind(self.exchange, routing_key=f"ts.client.{self.client_id}")
        await self.queue.purge() # 🔥 Deletes all unconsumed messages in this queue from previous runs

        # 4. Start consuming messages
        await self.queue.consume(self._rabbitmq_handler, no_ack=False)

        # 5. Register with TS (via publish)
        await self.exchange.publish(
            Message(
                body=json.dumps({
                    "command": "register",
                    "clientId": self.client_id
                }).encode()
            ),
            routing_key="py.register"
        )

        logging.info(f"✅ Client {self.client_id} connected and listening on ts.client.{self.client_id}")

    async def _rabbitmq_handler(self, message: IncomingMessage):
        try:
            payload = json.loads(message.body.decode())
            # logging.info(f"📩 Received RabbitMQ message for {self.client_id}: {payload}")
            self._handle_message(payload)
        except Exception as e:
            logging.info(f"❌ Failed to parse message: {e}")
            await message.nack(requeue=False)  # Don't requeue broken payloads
    
    async def _handle_and_ack(self, message: IncomingMessage, payload):
        try:
            self._handle_message(payload)
            await message.ack()
        except Exception as e:
            logging.info(f"❌ Error handling message in background task: {e}")
            await message.nack(requeue=False)

    async def send_to_ts(self, data: dict):
        """Send message to TS via RabbitMQ."""
        if self.exchange is None:
            logging.info("❌ Cannot send message: exchange not ready.")
            return

        await self.exchange.publish(
            Message(body=json.dumps(data).encode()),
            routing_key=f"py.client.{self.client_id}"
        )
        # logging.info(f"📤 Sent to TS [py.client.{self.client_id}] -> {data}")

    def _handle_message(self, data: dict):
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
            inter_conversation_time = time.time() - self.last_conversation_start_timestamp
            metrics.log_inter_conversation_time(self.client_id, sender, conversation_id, inter_conversation_time)
            self.last_conversation_start_timestamp = time.time()
            # logging.info(f"🆕 Received start of new conversation [{sender} -> {self.client_id}] [Conv: {conversation_id}] (Type: {conversation_type}, expected_number_of_messages: {expected_number_of_messages}s)")
        
        # Update the conversation object
        self.ongoing_conversations[conversation_id]["last_message_time"] = time.time()
        self.ongoing_conversations[conversation_id]["messages_exchanged"] = int(self.ongoing_conversations[conversation_id]["messages_exchanged"]) + 1
        
        logging.info(f'📩 Received Message [{sender} -> {self.client_id}] --- Conv: {conversation_id} --- Message number: {self.ongoing_conversations[conversation_id]["messages_exchanged"]}/{self.ongoing_conversations[conversation_id]["expected_number_of_messages"]}')
        
        if int(self.ongoing_conversations[conversation_id]["messages_exchanged"]) >= int(self.ongoing_conversations[conversation_id]["expected_number_of_messages"]) or message_text == "END_CONVERSATION":
            logging.info(f"🛑 Deleting conversation from memory [{sender} -> {self.client_id}]")

            # Cancel the associated async task if it's still running
            task = self.message_tasks.get(conversation_id)
            if task and not task.done():
                logging.info(f"🧹 Cancelling async task for conversation: {conversation_id}")
                task.cancel()
            
            # Cleanup
            self.message_tasks.pop(conversation_id, None)
            self.ongoing_conversations.pop(conversation_id, None)
        else:
            last_id = str(self.ongoing_conversations[conversation_id].get("last_message_burst_block_id", "")).strip()
            incoming_id = str(message_burst_block_id).strip()
            if last_id != incoming_id and conversation_id not in self.message_tasks:
                self.ongoing_conversations[conversation_id]["last_message_burst_block_id"] = incoming_id
                task = asyncio.create_task(self._respond_to_message(sender, conversation_id))
                self.message_tasks[conversation_id] = task
            else:
                logging.info("Already responding to message from same burst block.")
                

    async def _respond_to_message(self, sender, conversation_id):
        """Respond to the received message."""
        conversation_obj = self.ongoing_conversations[conversation_id]
        conversation_type = conversation_obj["conversation_type"]
        expected_number_of_messages = conversation_obj["expected_number_of_messages"]
        conversation_type = utils.get_conversation_type()
        delay = utils.get_response_delay(conversation_type) * 60 # min to sec
        logging.info(f"⏳ Delay until next Message [{self.client_id} -> {sender}] --- Conv: {conversation_id} --- {delay:.2f}sec")
        await asyncio.sleep(delay)
        if conversation_id in self.ongoing_conversations: # Fail safe mechanism in case conversation got stopped/deleted in the meantime
            metrics.log_response_time(self.client_id, sender, conversation_id, delay)
            await self._send_message(sender, conversation_id, conversation_type, expected_number_of_messages)

    async def _send_message(self, recipient, conversation_id, conversation_type="sync", expected_number_of_messages=4):
        """Send a burst block of messages in a conversation."""
        message_burst_block_id = str(uuid.uuid4())
        burst_size = utils.get_bursty_consecutive_messages()
        # burst_size = 1

        for i in range(burst_size):
            if conversation_id not in self.ongoing_conversations:
                break  # Fail-safe: conversation may have ended

            convo = self.ongoing_conversations[conversation_id]
            convo["messages_exchanged"] += 1
            message_index = convo["messages_exchanged"]
            max_messages = convo["expected_number_of_messages"]

            # Determine message content
            is_last_message = message_index >= max_messages
            message_text = "END_CONVERSATION" if is_last_message else messaging.generate_message_text(utils.get_message_size())

            # Build message payload
            message_content = {
                "messageId": str(uuid.uuid4()),
                "messageBurstBlockId": message_burst_block_id,
                "conversationId": conversation_id,
                "conversationType": conversation_type,
                "expectedNumberOfMessages": expected_number_of_messages,
                "additionalText": message_text
            }

            payload = {
                "command": "send",
                "clientId": str(self.client_id),
                "recipientId": str(recipient),
                "message_content": json.dumps(message_content)
            }

            logging.info(f'📤 Sending Message [{self.client_id} -> {recipient}] — Conv: {conversation_id} — Message {message_index}/{max_messages} - Burst {i+1}/{burst_size}')
            await self.send_to_ts(payload)

            # Debug conversation state
            ongoing_ids = " | ".join(self.ongoing_conversations.keys())
            logging.info(f"[{self.client_id}] Active Conversations: {len(self.ongoing_conversations)} -> {ongoing_ids}")

            # End condition
            if is_last_message:
                logging.info(f"\n🛑 Ending conversation [{self.client_id} -> {recipient}] — Conv: {convo}")
                self._log_end_of_conversation(recipient, conversation_id)
                del self.ongoing_conversations[conversation_id]
                break

            # Delay before next message in burst
            delay_seconds = utils.get_bursty_message_delay() * 60
            await asyncio.sleep(delay_seconds)
        
        self.message_tasks.pop(conversation_id, None)

    async def _simulate_behavior(self):
        """Randomly initiates conversations at different times."""
        while True:
            planned_inter_conversation_time = utils.get_inter_conversation_time()
            await asyncio.sleep(planned_inter_conversation_time * 60) # min to sec
            recipient = utils.choose_recipient(self.connections)
            if conversation.can_start_new_conversation(recipient, self.ongoing_conversations):
                await self._initiate_conversation(recipient)

    def _log_end_of_conversation(self, sender, conversation_id):
        """End the conversation and log its duration."""
        duration_sec = time.time() - self.ongoing_conversations[conversation_id]["start_time"]
        duration_min = duration_sec / 60.0
        metrics.log_conversation_duration(self.client_id, sender, conversation_id, duration_min)
        metrics.log_number_of_messages(self.client_id, sender, conversation_id, self.ongoing_conversations[conversation_id]["messages_exchanged"])

    async def _initiate_conversation(self, recipient):
        """Initiate a new conversation."""
        conversation_id = conversation.generate_conversation_id(self.client_id, recipient)
        expected_number_of_messages = utils.get_expected_number_of_messages_for_conversation()
        conversation_type = utils.get_conversation_type()
        
        self.ongoing_conversations[conversation_id] = conversation.create_conversation_obj(recipient, conversation_type, expected_number_of_messages)
        logging.info(f"📢 Initiating conversation [{self.client_id} -> {recipient}] --- Conv: {self.ongoing_conversations[conversation_id]}")
        inter_conversation_time = time.time() - self.last_conversation_start_timestamp
        metrics.log_inter_conversation_time(self.client_id, recipient, conversation_id, inter_conversation_time)
        self.last_conversation_start_timestamp = time.time()
    
        await self._send_message(recipient, conversation_id, conversation_type, expected_number_of_messages)

    async def run(self):
        """Run the client, connecting and listening for messages."""
        self.loop = asyncio.get_event_loop()
        await self._connect()
        asyncio.create_task(self._simulate_behavior())
        await asyncio.Future()  # Keeps it alive