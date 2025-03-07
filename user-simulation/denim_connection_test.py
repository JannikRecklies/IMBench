import asyncio
import websockets
import json
import numpy as np

# WebSocket connection details
WEBSOCKET_URI = "ws://127.0.0.1:8081"

# Clients to register
clients = ["1", "2", "3"]

# Define response delay function (exponential distribution for natural delays)
def response_delay():
    return max(1, np.random.exponential(scale=3))  # Min delay 1s, avg 3s

async def register_clients(ws):
    """Register all clients with the TypeScript WebSocket server."""
    for client_id in clients:
        await ws.send(json.dumps({"command": "register", "clientId": client_id}))
        await asyncio.sleep(1)  # Ensure sequential registration

async def send_response(ws, clientId, recipientId):
    """Send a delayed response message."""
    response_text = f"Auto-response from {clientId}"
    await ws.send(json.dumps({
        "command": "send",
        "clientId": clientId,
        "recipientId": recipientId,
        "text": response_text,
        "delay": 0  # Immediate send after waiting
    }))
    print(f"📤 {clientId} → {recipientId}: {response_text}")

async def handle_message(ws, message):
    """Handle received messages and schedule responses."""
    data = json.loads(message)

    if data.get("event") == "message_received":
        sender = data["sender"]
        receiver = data["clientId"]
        received_message = data["message"]
        delay = response_delay()  # Generate a probabilistic delay in seconds

        print(f"📩 {receiver} received from {sender}: {received_message} (responding in {delay:.2f}s)")
        
        # Schedule response
        await asyncio.sleep(delay)
        await send_response(ws, receiver, sender)

async def websocket_client():
    """Main async WebSocket client to communicate with TypeScript."""
    async with websockets.connect(WEBSOCKET_URI) as ws:
        print("✅ Connected to TypeScript WebSocket server.")

        # Register clients
        await register_clients(ws)

        # Listen for incoming messages
        async for message in ws:
            await handle_message(ws, message)

# Run the WebSocket client
asyncio.run(websocket_client())