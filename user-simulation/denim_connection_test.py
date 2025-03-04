import asyncio
import websockets
import json

# Server address (Modify if needed)
DENIM_SERVER_URL = "ws://130.238.29.99:8080"

# Dummy users
USERS = {
    "user1": {"id": "user1", "name": "Alice"},
    "user2": {"id": "user2", "name": "Bob"}
}

async def send_message(websocket, sender, receiver):
    """Send a message from sender to receiver"""
    message = {
        "type": "MESSAGE",
        "from": sender["id"],
        "to": receiver["id"],
        "content": f"Hello from {sender['name']}!"
    }
    await websocket.send(json.dumps(message))
    print(f"📤 {sender['name']} sent message to {receiver['name']}")

async def receive_messages(websocket, user):
    """Receive messages for a user"""
    async for msg in websocket:
        data = json.loads(msg)
        print(f"📩 {user['name']} received: {data}")

async def client(user, peer):
    """Each client connects, sends messages, and listens"""
    async with websockets.connect(DENIM_SERVER_URL) as websocket:
        print(f"✅ {user['name']} connected to DenIM")

        # Task to receive messages
        asyncio.create_task(receive_messages(websocket, user))

        # Send messages every 10 seconds
        while True:
            await send_message(websocket, user, peer)
            await asyncio.sleep(10)

async def main():
    """Run both clients concurrently"""
    await asyncio.gather(
        client(USERS["user1"], USERS["user2"]),
        client(USERS["user2"], USERS["user1"])
    )

# Start clients
asyncio.run(main())