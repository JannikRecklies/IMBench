import asyncio
import websockets
import json
from client import Client

WEBSOCKET_URI = "ws://127.0.0.1:8081"

# Define clients (example with 3 users)
clients = {
    "1": Client("1", ["2", "3"], [0.6, 0.1]),
    "2": Client("2", ["1", "3"], [0.6, 0.5]),
    "3": Client("3", ["1", "2"], [0.1, 0.5]),
}

async def register_clients(ws):
    """Registers all clients with TypeScript."""
    for client_id in clients:
        await ws.send(json.dumps({"command": "register", "clientId": client_id}))
        await asyncio.sleep(1)  # Delay to avoid overload

async def send_message(ws, sender, recipient, text):
    """Sends a message between clients."""
    await ws.send(json.dumps({
        "command": "send",
        "clientId": sender,
        "recipientId": recipient,
        "text": text
    }))
    # print(f"📤 {sender} → {recipient}: {text}")

async def handle_message(ws, message):
    """Handles incoming messages and schedules responses."""
    data = json.loads(message)

    if data.get("event") == "message_received":
        sender = data["sender"]
        receiver = data["clientId"]
        received_message = data["message"]
        client = clients[receiver]

        # print(f"📩 {receiver} received from {sender}: {received_message}")

        if client.get_message_end_probability():
            print(f"🛑 {receiver} is ending conversation with {sender}.")
            return  # Stop responding

        delay = client.get_response_delay()
        # print(f"⏳ {receiver} will respond in {delay:.2f}s")
        await asyncio.sleep(delay)

        await send_message(ws, receiver, sender, f"Reply from {receiver}")

async def simulate_behavior(ws):
    """Checks if clients should start conversations."""
    while True:
        for client_id, client in clients.items():
            if client.should_initiate_conversation():
                recipient = client.choose_recipient()
                print(f"📢 {client_id} initiates conversation with {recipient}")
                await send_message(ws, client_id, recipient, "Hello!")
        await asyncio.sleep(5)  # Check every 5s

async def websocket_client():
    """Main WebSocket loop."""
    async with websockets.connect(WEBSOCKET_URI, ping_interval=None) as ws:
        print("✅ Connected to TypeScript WebSocket server.")
        await register_clients(ws)  # Register clients
        
        asyncio.create_task(simulate_behavior(ws))  # Start behavior simulation

        async for message in ws:
            await handle_message(ws, message)


asyncio.run(websocket_client())