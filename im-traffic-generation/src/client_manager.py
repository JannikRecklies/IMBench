import asyncio
import websockets
import json
import threading
from user_behavior_simulation.client import Client
from social_graph_generation.social_graph_generator import generate_hk_graph, assign_edge_weights

WEBSOCKET_URI = "ws://127.0.0.1:8081"
NUMBER_CLIENTS = 100



def create_clients_from_graph():
    """Generates a social graph and initializes clients based on it."""
    G = generate_hk_graph(n=NUMBER_CLIENTS)
    weighted_graph, weights = assign_edge_weights(G)
   
    clients = {}
    for node in weighted_graph.nodes():
        neighbors = list(weighted_graph.neighbors(node))
        connections = [(neighbor, weighted_graph[node][neighbor]["weight"]) for neighbor in neighbors]

        clients[node] = Client(client_id=node, connections=connections, ws_uri=WEBSOCKET_URI)
    return clients

def start_client(client):
    """Runs each client as a separate async thread."""
    asyncio.run(client.run())

async def main():
    """Main function to start all clients."""
    clients = create_clients_from_graph()

    # Start each client in a separate thread
    for client in clients.values():
        thread = threading.Thread(target=start_client, args=(client,))
        thread.start()
        #await asyncio.sleep(0.5)  # Small delay to avoid overload

asyncio.run(main())