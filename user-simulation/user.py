import random
import time

class User:
    def __init__(self, user_id, neighbors, edge_weights):
        """Initialize user with neighbors and connection weights."""
        self.user_id = user_id
        self.neighbors = neighbors
        self.edge_weights = edge_weights  # Dict {neighbor_id: weight}
        self.activity_level = self.estimate_activity_level()

    def estimate_activity_level(self):
        """Estimate user activity level based on connection strengths."""
        return sum(self.edge_weights.values()) / len(self.edge_weights) if self.edge_weights else 0

    def select_interaction_partner(self):
        """Select a neighbor to message, based on weighted probability."""
        if not self.neighbors:
            return None
        return random.choices(self.neighbors, weights=self.edge_weights.values(), k=1)[0]

    def send_message(self, target_user):
        """Simulate sending a message to a selected target user."""
        print(f"User {self.user_id} -> User {target_user}: 📩 Message sent!")

    def run(self, duration=10):
        """Simulate user activity over a set duration."""
        start_time = time.time()
        while time.time() - start_time < duration:
            time.sleep(random.uniform(0.5, 2))  # Simulate random activity delays
            target = self.select_interaction_partner()
            if target:
                self.send_message(target)