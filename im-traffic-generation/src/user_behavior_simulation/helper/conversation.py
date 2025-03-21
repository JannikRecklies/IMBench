import time
from scipy.stats import powerlaw
import user_behavior_simulation.helper.utils as utils

def generate_conversation_id(client_id, recipient):
    timestamp = int(time.time() * 1000)
    return f"{client_id}_{recipient}_{timestamp}"

def should_conversation_end(conversation):
    elapsed_time = time.time() - conversation["start_time"]
    return elapsed_time > conversation["duration"]

def create_conversation_obj(recipient):
    return {
        "start_time": time.time(),
        "last_message_time": time.time(),
        "duration": utils.get_conversation_duration(),
        "recipient": recipient
    }

def can_start_new_conversation(recipient, ongoing_conversations):
        """Check if a new conversation can be started with the recipient."""
        ongoing = any(str(conv["recipient"]) == str(recipient) for conv in ongoing_conversations.values())
        return recipient and not ongoing

def is_end_of_conversation_message(message_text, conversation_id, ongoing_conversations):
        """Handle conversation end acknowledgment."""
        if message_text == "END_CONVERSATION" and conversation_id in ongoing_conversations:
            return True
        else:
            return False