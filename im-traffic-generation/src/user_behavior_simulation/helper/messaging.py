import uuid
import json

def generate_message_content(conversation_id, text="Hello!"):
    message_id = str(uuid.uuid4())
    message_content = {
        "message_id": message_id,
        "conversation_id": conversation_id,
        "text": text
    }
    return json.dumps(message_content)

def extract_message_info(data):
        """Extract sender, conversation ID, and message text from the data."""
        sender = data["sender"]
        received_message = data["message_content"]
        json_received_message = json.loads(received_message)
        conversation_id = json_received_message.get("conversation_id")
        message_text = json_received_message.get("text")
        return sender, conversation_id, message_text

def is_relevant_message(data, client_id):
    """Check if the message is relevant to this client."""
    return data.get("event") == "message_received" and str(data["clientId"]) == str(client_id)
