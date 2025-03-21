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