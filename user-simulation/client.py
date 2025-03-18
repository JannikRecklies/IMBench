import random
import numpy as np
import asyncio

class Client:
    def __init__(self, client_id, connected_clients, connection_strengths):
        self.client_id = client_id  # Unique identifier
        self.connected_clients = connected_clients  # List of clients it can talk to
        self.connection_strengths = connection_strengths  # Connection probabilities

    def should_initiate_conversation(self):
        """Decides if this client should start a conversation."""
        return random.random() < 0.1  # Example: 10% chance of starting a convo

    def get_response_delay(self):
        """Calculates how long to wait before responding (power-law or exponential)."""
        return max(1, np.random.exponential(scale=3))  # Min delay 1s, avg 3s

    def get_message_end_probability(self):
        """Returns probability of ending conversation."""
        return random.random() < 0.05  # Example: 5% chance to stop talking

    def choose_recipient(self):
        """Selects a recipient based on connection strengths."""
        return random.choices(self.connected_clients, weights=self.connection_strengths, k=1)[0]