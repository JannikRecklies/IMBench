import asyncio
import websockets
import json

# WebSocket connection details
WEBSOCKET_URI = "ws://127.0.0.1:8081"

# Define clients for conversation
client_A = "1"  # Initiator
client_B = "2"  # Responder

# Fixed delay of 5 seconds between messages
RESPONSE_DELAY = 5

async def register_clients(ws):
    """Register the two clients with the TypeScript WebSocket server."""
    for client_id in [client_A, client_B]:
        await ws.send(json.dumps({"command": "register", "clientId": client_id}))
        await asyncio.sleep(1)  # Ensure sequential registration

async def send_message(ws, sender, receiver, text):
    """Send a message from one client to another."""
    await ws.send(json.dumps({
        "command": "send",
        "clientId": sender,
        "recipientId": receiver,
        "text": text,
        "delay": 0  # Immediate send
    }))
    print(f"📤 {sender} → {receiver}: {text}")

async def handle_message(ws, message):
    """Handle received messages and schedule responses."""
    data = json.loads(message)

    if data.get("event") == "message_received":
        sender = data["sender"]
        receiver = data["clientId"]
        received_message = data["message"]

        print(f"📩 {receiver} received from {sender}: {received_message} (responding in {RESPONSE_DELAY}s)")

        # Wait for the delay, then respond
        await asyncio.sleep(RESPONSE_DELAY)
        await send_message(ws, receiver, sender, f"Reply from {receiver}")

async def websocket_client():
    """Main async WebSocket client to communicate with TypeScript."""
    async with websockets.connect(WEBSOCKET_URI) as ws:
        print("✅ Connected to TypeScript WebSocket server.")

        # Register both clients
        await register_clients(ws)

        # Start the conversation (client_A initiates)
        await asyncio.sleep(2)  # Short delay before starting
        await send_message(ws, client_A, client_B, "Hello from client A!")

        # Listen for responses and continue ping-pong messaging
        async for message in ws:
            await handle_message(ws, message)

# Run the WebSocket client
asyncio.run(websocket_client())