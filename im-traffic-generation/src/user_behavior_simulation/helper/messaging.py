import uuid
import json

def extract_message_info(data):
    """Extract sender, conversation ID, message text, conversation type, and expected duration from the message_content."""
    sender = data["sender"]
    received_message = data["message_content"]
    
    message_content = json.loads(received_message)
    conversation_id = message_content.get("conversationId")
    conversation_type = message_content.get("conversationType", "sync")  # Default to "sync" if not specified
    expected_duration = message_content.get("expectedDuration", 300)  # Default to 300 seconds if not specified
    message_text = message_content.get("additionalText")
    return sender, conversation_id, message_text, conversation_type, expected_duration

def is_relevant_message(data, client_id):
    """Check if the message is relevant to this client."""
    return data.get("event") == "message_received" and str(data["clientId"]) == str(client_id)
