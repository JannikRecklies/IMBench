import asyncio
import websockets

# DenIM WebSocket Server Address (Update if necessary)
DENIM_SERVER_URL = "ws://130.238.29.99:8080"

async def client(identifier):
    """Connects a client to the DenIM WebSocket and exchanges messages."""
    async with websockets.connect(DENIM_SERVER_URL) as ws:
        print(f"{identifier} connected to DenIM.")

        # Send initial message
        await ws.send(f"{identifier}: Hello from {identifier}!")
        print(f"{identifier} → Sent initial message.")

        while True:
            try:
                # Wait for incoming messages
                response = await ws.recv()
                print(f"{identifier} ← Received: {response}")

                # Send a message every 5 seconds
                await asyncio.sleep(5)
                await ws.send(f"{identifier}: Ping!")
                print(f"{identifier} → Sent: Ping!")

            except websockets.exceptions.ConnectionClosed:
                print(f"{identifier} disconnected from server.")
                break

# Run two clients in parallel
async def main():
    client1 = asyncio.create_task(client("user1"))
    client2 = asyncio.create_task(client("user2"))

    await asyncio.gather(client1, client2)

if __name__ == "__main__":
    asyncio.run(main())