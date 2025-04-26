import asyncio
import threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
import uvicorn

from user_behavior_simulation.client import Client
from social_graph_generation.social_graph_generator import generate_hk_graph, assign_edge_weights_powerlaw

app = FastAPI()

# Global state
clients: Dict[int, Client] = {}
threads: Dict[int, threading.Thread] = {}
experiment_running = False

class ExperimentConfig(BaseModel):
    number_of_clients: int

@app.post("/start")
async def start_experiment(config: ExperimentConfig):
    global clients, threads, experiment_running

    if experiment_running:
        raise HTTPException(status_code=400, detail="Experiment is already running.")

    G = generate_hk_graph(n=config.number_of_clients)
    weighted_graph, _ = assign_edge_weights_powerlaw(G)

    clients = {}
    threads = {}

    for node in weighted_graph.nodes():
        neighbors = list(weighted_graph.neighbors(node))
        connections = [(neighbor, weighted_graph[node][neighbor]["weight"]) for neighbor in neighbors]
        clients[node] = Client(client_id=node, connections=connections)

    def run_client(client: Client):
        asyncio.run(client.run())

    for client_id, client in clients.items():
        thread = threading.Thread(target=run_client, args=(client,), daemon=True)
        thread.start()
        threads[client_id] = thread

    experiment_running = True
    return {"status": "Experiment started", "clients": config.number_of_clients}

@app.post("/stop")
async def stop_experiment():
    global experiment_running

    if not experiment_running:
        raise HTTPException(status_code=400, detail="No experiment is currently running.")

    for client in clients.values():
        client.stop()  # This method should gracefully shut down the client

    clients.clear()
    threads.clear()
    experiment_running = False

    return {"status": "Experiment stopped"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)