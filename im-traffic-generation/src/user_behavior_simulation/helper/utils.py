import random
import numpy as np
import os
import user_behavior_simulation.helper.distributions as distributions

INTER_CONVERSATION_TIME_MODE = float(os.getenv("INTER_CONVERSATION_TIME_MODE", 1))
INTER_CONVERSATION_TIME_MINIMUM = float(os.getenv("INTER_CONVERSATION_TIME_MINIMUM", 0.1))
INTER_CONVERSATION_TIME_MAXIMUM = float(os.getenv("INTER_CONVERSATION_TIME_MAXIMUM", 120))

CONVERSATION_DURATION_MODE = float(os.getenv("CONVERSATION_DURATION_MODE", 4))
CONVERSATION_DURATION_MINIMUM = float(os.getenv("CONVERSATION_DURATION_MINIMUM", 1))
CONVERSATION_DURATION_MAXIMUM = float(os.getenv("CONVERSATION_DURATION_MAXIMUM", 6*60))

MESSAGES_PER_CONVERSATION_MODE = int(os.getenv("MESSAGES_PER_CONVERSATION_MODE", 4))
MESSAGES_PER_CONVERSATION_MINIMUM = int(os.getenv("MESSAGES_PER_CONVERSATION_MINIMUM", 1))
MESSAGES_PER_CONVERSATION_MAXIMUM = int(os.getenv("MESSAGES_PER_CONVERSATION_MAXIMUM", 200))

SYNC_TO_ASYNC_CONVERSATION_RATIO = float(os.getenv("SYNC_TO_ASYNC_CONVERSATION_RATIO", 0.5))

SYNC_CONVERSATION_RESPONSE_TIME_MODE = float(os.getenv("SYNC_CONVERSATION_RESPONSE_TIME_MODE", (20.0/60.0)))
SYNC_CONVERSATION_RESPONSE_TIME_MINIMUM = float(os.getenv("SYNC_CONVERSATION_RESPONSE_TIME_MINIMUM", (1.0/60.0)))
SYNC_CONVERSATION_RESPONSE_TIME_MAXIMUM = float(os.getenv("SYNC_CONVERSATION_RESPONSE_TIME_MAXIMUM", (60.0/60.0)))

ASYNC_CONVERSATION_RESPONSE_TIME_MODE = float(os.getenv("ASYNC_CONVERSATION_RESPONSE_TIME_MODE", 6.0))
ASYNC_CONVERSATION_RESPONSE_TIME_MINIMUM = float(os.getenv("ASYNC_CONVERSATION_RESPONSE_TIME_MINIMUM", 1.0))
ASYNC_CONVERSATION_RESPONSE_TIME_MAXIMUM = float(os.getenv("ASYNC_CONVERSATION_RESPONSE_TIME_MAXIMUM", 18.0))

messages_per_conversation_lognorm_distr = distributions.create_lognormal_distribution(mode=MESSAGES_PER_CONVERSATION_MODE, min_value=MESSAGES_PER_CONVERSATION_MINIMUM, max_value=MESSAGES_PER_CONVERSATION_MAXIMUM)
inter_conversation_time_lognorm_distr = distributions.create_lognormal_distribution(mode=INTER_CONVERSATION_TIME_MODE, min_value=INTER_CONVERSATION_TIME_MINIMUM, max_value=INTER_CONVERSATION_TIME_MAXIMUM)
conversation_duration_lognorm_distr = distributions.create_lognormal_distribution(mode=CONVERSATION_DURATION_MODE, min_value=CONVERSATION_DURATION_MINIMUM, max_value=CONVERSATION_DURATION_MAXIMUM)
sync_conversation_response_time_lognorm_distr = distributions.create_lognormal_distribution(mode=SYNC_CONVERSATION_RESPONSE_TIME_MODE, min_value=SYNC_CONVERSATION_RESPONSE_TIME_MINIMUM, max_value=SYNC_CONVERSATION_RESPONSE_TIME_MAXIMUM)
async_conversation_response_time_lognorm_distr = distributions.create_lognormal_distribution(mode=ASYNC_CONVERSATION_RESPONSE_TIME_MODE, min_value=ASYNC_CONVERSATION_RESPONSE_TIME_MINIMUM, max_value=ASYNC_CONVERSATION_RESPONSE_TIME_MAXIMUM)

messages_per_conversation_samples = [distributions.generate_lognormal_value(messages_per_conversation_lognorm_distr, MESSAGES_PER_CONVERSATION_MINIMUM, MESSAGES_PER_CONVERSATION_MAXIMUM) for _ in range(10000)]

def get_response_delay(conversation_type):
    if random.random() < SYNC_TO_ASYNC_CONVERSATION_RATIO:
        return distributions.generate_lognormal_value(sync_conversation_response_time_lognorm_distr, SYNC_CONVERSATION_RESPONSE_TIME_MINIMUM, SYNC_CONVERSATION_RESPONSE_TIME_MAXIMUM)
    else:
        return distributions.generate_lognormal_value(async_conversation_response_time_lognorm_distr, ASYNC_CONVERSATION_RESPONSE_TIME_MINIMUM, ASYNC_CONVERSATION_RESPONSE_TIME_MAXIMUM)

def get_conversation_type_threshold():
    return np.percentile(messages_per_conversation_samples, SYNC_TO_ASYNC_CONVERSATION_RATIO * 100)

def get_conversation_type():
    return "sync" if random.random() < SYNC_TO_ASYNC_CONVERSATION_RATIO else "async"

def get_expected_number_of_messages_for_conversation():
    return int(distributions.generate_lognormal_value(messages_per_conversation_lognorm_distr, MESSAGES_PER_CONVERSATION_MINIMUM, MESSAGES_PER_CONVERSATION_MAXIMUM))

# obsolete
def get_conversation_duration():
    return distributions.generate_lognormal_value(conversation_duration_lognorm_distr, CONVERSATION_DURATION_MINIMUM, CONVERSATION_DURATION_MAXIMUM)

def get_inter_conversation_time():
    return distributions.generate_lognormal_value(inter_conversation_time_lognorm_distr, INTER_CONVERSATION_TIME_MINIMUM, INTER_CONVERSATION_TIME_MAXIMUM)

def choose_recipient(connections):
    if not connections:
        return None
    neighbors, weights = zip(*connections)
    return random.choices(neighbors, weights=weights, k=1)[0]