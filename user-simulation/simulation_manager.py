import networkx as nx
import threading
import time
from social_graph_generator import generate_hk_graph  # Change to the desired graph model
from user import User

class SimulationManager:
    def __init__(self, num_users):
        """Initialize the simulation by generating a graph and creating users."""
        self.graph = generate_hk_graph(num_users)  # Generate social network graph
        self.users = self.create_users()

    def create_users(self):
        """Create user objects based on the generated social network."""
        users = {}
        for node in self.graph.nodes():
            neighbors = list(self.graph.neighbors(node))
            edge_weights = {neighbor: self.graph[node][neighbor]['weight'] for neighbor in neighbors}
            users[node] = User(node, neighbors, edge_weights)  # Instantiate user
        return users

    def run_simulation(self, duration=10):
        """Run the simulation where all users act in parallel."""
        threads = []
        for user in self.users.values():
            thread = threading.Thread(target=user.run, args=(duration,))
            threads.append(thread)
            thread.start()

        # Wait for all users to finish
        for thread in threads:
            thread.join()

if __name__ == "__main__":
    num_users = 100  # Define the size of the social graph
    sim_manager = SimulationManager(num_users)
    sim_manager.run_simulation(duration=60)  # Run for 20 seconds