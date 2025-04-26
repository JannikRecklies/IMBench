import random
import time
from scipy.stats import powerlaw
import user_behavior_simulation.helper.utils as utils

def generate_conversation_id(client_id, recipient):
    timestamp = int(time.time() * 1000)
    return f"{client_id}_{recipient}_{timestamp}"

def should_conversation_end(conversation):
    elapsed_time = time.time() - conversation["start_time"]
    return elapsed_time > conversation["duration"]

def create_conversation_obj(recipient, conversation_type="sync", expected_number_of_messages=4):
    return {
        "start_time": time.time(),
        "last_message_time": time.time(),
        "recipient": recipient,
        "conversation_type": conversation_type,
        "messages_exchanged": 0,
        "expected_number_of_messages": expected_number_of_messages,
        "last_message_burst_block_id": None
    }

# obsolete
def can_start_new_conversation(recipient, ongoing_conversations):
    """Check if a new conversation can be started with the recipient."""
    ongoing = any(str(conv["recipient"]) == str(recipient) for conv in ongoing_conversations.values())
    return recipient and not ongoing and len(ongoing_conversations) <= 5

def should_start_new_conversation(recipient, weight, ongoing_conversations, max_conversations=5):
    """Decides probabilistically if a new conversation should be started based on connection strength."""
    if not recipient or len(ongoing_conversations) >= max_conversations:
        return False

    # Boost weak connections slightly (optional)
    adjusted_weight = 0.2 + 0.8 * weight  # ensures min 10% chance even for weakest ties

    return random.random() < adjusted_weight

def is_end_of_conversation_message(message_text, conversation_id, ongoing_conversations):
    """Handle conversation end acknowledgment."""
    return message_text == "END_CONVERSATION" and conversation_id in ongoing_conversations