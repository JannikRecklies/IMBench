import random
import numpy as np
import os
import user_behavior_simulation.helper.distributions as distributions

INTER_CONVERSATION_TIME_ALPHA = float(os.getenv("INTER_CONVERSATION_TIME_ALPHA", 1.5)) # Minutes
INTER_CONVERSATION_TIME_MINIMUM = float(os.getenv("INTER_CONVERSATION_TIME_MINIMUM", 0.1))
INTER_CONVERSATION_TIME_MAXIMUM = float(os.getenv("INTER_CONVERSATION_TIME_MAXIMUM", 480))

SYNC_TO_ASYNC_CONVERSATION_RATIO = float(os.getenv("SYNC_TO_ASYNC_CONVERSATION_RATIO", 0.5)) # Percentage 0-1

SYNC_CONVERSATION_RESPONSE_TIME_MODE = float(os.getenv("SYNC_CONVERSATION_RESPONSE_TIME_MODE", (20.0/60.0))) # Minutes
SYNC_CONVERSATION_RESPONSE_TIME_MINIMUM = float(os.getenv("SYNC_CONVERSATION_RESPONSE_TIME_MINIMUM", (1.0/60.0)))
SYNC_CONVERSATION_RESPONSE_TIME_MAXIMUM = float(os.getenv("SYNC_CONVERSATION_RESPONSE_TIME_MAXIMUM", (120.0/60.0)))

ASYNC_CONVERSATION_RESPONSE_TIME_MODE = float(os.getenv("ASYNC_CONVERSATION_RESPONSE_TIME_MODE", 6.0)) # Minutes
ASYNC_CONVERSATION_RESPONSE_TIME_MINIMUM = float(os.getenv("ASYNC_CONVERSATION_RESPONSE_TIME_MINIMUM", 1.0))
ASYNC_CONVERSATION_RESPONSE_TIME_MAXIMUM = float(os.getenv("ASYNC_CONVERSATION_RESPONSE_TIME_MAXIMUM", 30.0))

MESSAGES_PER_CONVERSATION_MODE = int(os.getenv("MESSAGES_PER_CONVERSATION_MODE", 6)) # Number of messages
MESSAGES_PER_CONVERSATION_MINIMUM = int(os.getenv("MESSAGES_PER_CONVERSATION_MINIMUM", 1))
MESSAGES_PER_CONVERSATION_MAXIMUM = int(os.getenv("MESSAGES_PER_CONVERSATION_MAXIMUM", 200))

BURSTY_CONSECUTIVE_MESSAGES_ALPHA = int(os.getenv("BURSTY_CONSECUTIVE_MESSAGES_ALPHA", 3)) # Number of messages
BURSTY_CONSECUTIVE_MESSAGES_MINIMUM = int(os.getenv("BURSTY_CONSECUTIVE_MESSAGES_MINIMUM", 1))
BURSTY_CONSECUTIVE_MESSAGES_MAXIMUM = int(os.getenv("BURSTY_CONSECUTIVE_MESSAGES_MAXIMUM", 10))

BURSTY_MESSAGE_DELAY_MODE = float(os.getenv("BURSTY_MESSAGE_DELAY_MODE", (5.0/60.0))) # Minutes
BURSTY_MESSAGE_DELAY_MINIMUM = float(os.getenv("BURSTY_MESSAGE_DELAY_MINIMUM", (1.0/60.0)))
BURSTY_MESSAGE_DELAY_MAXIMUM = float(os.getenv("BURSTY_MESSAGE_DELAY_MAXIMUM", (30.0/60.0)))

TEXT_SIZE_MODE = int(os.getenv("TEXT_SIZE_MODE", 20)) # Bytes
TEXT_SIZE_MINIMUM = int(os.getenv("TEXT_SIZE_MINIMUM", 1))
TEXT_SIZE_MAXIMUM = int(os.getenv("TEXT_SIZE_MAXIMUM", 500))

sync_conversation_response_time_lognorm_distr = distributions.create_lognormal_distribution(mode=SYNC_CONVERSATION_RESPONSE_TIME_MODE, min_value=SYNC_CONVERSATION_RESPONSE_TIME_MINIMUM, max_value=SYNC_CONVERSATION_RESPONSE_TIME_MAXIMUM)
async_conversation_response_time_lognorm_distr = distributions.create_lognormal_distribution(mode=ASYNC_CONVERSATION_RESPONSE_TIME_MODE, min_value=ASYNC_CONVERSATION_RESPONSE_TIME_MINIMUM, max_value=ASYNC_CONVERSATION_RESPONSE_TIME_MAXIMUM)
messages_per_conversation_lognorm_distr = distributions.create_lognormal_distribution(mode=MESSAGES_PER_CONVERSATION_MODE, min_value=MESSAGES_PER_CONVERSATION_MINIMUM, max_value=MESSAGES_PER_CONVERSATION_MAXIMUM)
bursty_message_delay_lognorm_distr = distributions.create_lognormal_distribution(mode=BURSTY_MESSAGE_DELAY_MODE, min_value=BURSTY_MESSAGE_DELAY_MINIMUM, max_value=BURSTY_MESSAGE_DELAY_MAXIMUM)
text_size_distr = distributions.create_lognormal_distribution(TEXT_SIZE_MODE, TEXT_SIZE_MINIMUM, TEXT_SIZE_MAXIMUM)

def get_response_delay(conversation_type="sync"):
    if conversation_type == "sync":
        return distributions.generate_lognormal_value(sync_conversation_response_time_lognorm_distr, SYNC_CONVERSATION_RESPONSE_TIME_MINIMUM, SYNC_CONVERSATION_RESPONSE_TIME_MAXIMUM)
    elif conversation_type == "async":
        return distributions.generate_lognormal_value(async_conversation_response_time_lognorm_distr, ASYNC_CONVERSATION_RESPONSE_TIME_MINIMUM, ASYNC_CONVERSATION_RESPONSE_TIME_MAXIMUM)
    else:
        1.0 # Minute

def get_conversation_type():
    return "sync" if random.random() < SYNC_TO_ASYNC_CONVERSATION_RATIO else "async"

def get_expected_number_of_messages_for_conversation():
    return int(distributions.generate_lognormal_value(messages_per_conversation_lognorm_distr, MESSAGES_PER_CONVERSATION_MINIMUM, MESSAGES_PER_CONVERSATION_MAXIMUM))

def get_bursty_consecutive_messages():
    return int(distributions.generate_powerlaw_value(BURSTY_CONSECUTIVE_MESSAGES_ALPHA, BURSTY_CONSECUTIVE_MESSAGES_MINIMUM, BURSTY_CONSECUTIVE_MESSAGES_MAXIMUM))

def get_bursty_message_delay():
    return float(distributions.generate_lognormal_value(bursty_message_delay_lognorm_distr, BURSTY_MESSAGE_DELAY_MINIMUM, BURSTY_MESSAGE_DELAY_MAXIMUM))

def get_inter_conversation_time():
    return distributions.generate_powerlaw_value(INTER_CONVERSATION_TIME_ALPHA, INTER_CONVERSATION_TIME_MINIMUM, INTER_CONVERSATION_TIME_MAXIMUM)

def get_message_size():
    return int(distributions.generate_lognormal_value(text_size_distr, TEXT_SIZE_MINIMUM, TEXT_SIZE_MAXIMUM))

def choose_recipient(connections):
    if not connections:
        return None
    neighbors, weights = zip(*connections)
    return random.choices(neighbors, weights=weights, k=1)[0]