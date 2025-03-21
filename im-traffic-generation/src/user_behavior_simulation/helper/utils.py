import random
from scipy.stats import powerlaw

def get_response_delay():
    return 10

def get_conversation_duration():
    return max(30, powerlaw.rvs(3.7) * 240)

def get_inter_conversation_time():
    return max(5, powerlaw.rvs(1.5) * 60)

def should_initiate_conversation():
    return random.random() < 0.3

def choose_recipient(connections):
    if not connections:
        return None
    neighbors, weights = zip(*connections)
    return random.choices(neighbors, weights=weights, k=1)[0]