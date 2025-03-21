import time
from scipy.stats import powerlaw
import user_behavior_simulation.helper.utils as utils

def generate_conversation_id(client_id, recipient):
    timestamp = int(time.time() * 1000)
    return f"{client_id}_{recipient}_{timestamp}"

def has_conversation_ended(conversation):
    elapsed_time = time.time() - conversation["start_time"]
    return elapsed_time > conversation["duration"]

def create_conversation_obj(recipient):
    return {
        "start_time": time.time(),
        "last_message_time": time.time(),
        "duration": utils.get_conversation_duration(),
        "recipient": recipient
    }

def end_conversation(client_id, recipient, ongoing_conversations, conversation_id):
    duration = time.time() - ongoing_conversations[conversation_id]["start_time"]
    print(f"🛑 {client_id} ended conversation {conversation_id} with {recipient}. Duration: {duration}")
    del ongoing_conversations[conversation_id]