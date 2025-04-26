from collections import Counter
import numpy as np
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import user_behavior_simulation.helper.utils as utils

def _test_choose_recipient(connections, num_samples=10000):
    counts = Counter()

    for _ in range(num_samples):
        recipient = utils.choose_recipient(connections)
        counts[recipient] += 1

    # Sort by count descending
    sorted_counts = counts.most_common()

    print("Most selected recipients (top 5):")
    for recipient, count in sorted_counts:
        print(f"Node {recipient}: {count} times ({(count/num_samples)*100:.2f}%)")

    return counts

if __name__ == "__main__":
    # Define connections
    connections = [
        (0, np.float64(0.02)), (3, np.float64(0.03)), (1, np.float64(0.03)),
        (6, np.float64(0.09)), (7, np.float64(0.02)), (9, np.float64(0.03)),
        (14, np.float64(0.02)), (16, np.float64(0.03)), (21, np.float64(0.04)),
        (26, np.float64(0.05)), (30, np.float64(0.02)), (32, np.float64(0.05)),
        (36, np.float64(0.02)), (39, np.float64(0.14)), (40, np.float64(0.01))
    ]

    # Run the test
    counts = _test_choose_recipient(connections)
    