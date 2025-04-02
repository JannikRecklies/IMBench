from scipy.stats import powerlaw
from scipy.stats import lognorm
import numpy as np

def create_lognormal_distribution(mode, min_value, max_value, target_coverage=0.95, min_spread_ratio=0.5, max_tries=200):
    """
    Creates a log-normal distribution with a given mode, trying to ensure:
    - target_coverage of samples fall within [min_value, max_value]
    - the spread between p5 and p95 covers at least `min_spread_ratio` of the total range
    """
    for sigma in np.linspace(0.1, 10.0, max_tries):
        mu = np.log(mode) + sigma**2
        dist = lognorm(s=sigma, scale=np.exp(mu))

        p_low = dist.cdf(min_value)
        p_high = dist.cdf(max_value)
        coverage = p_high - p_low

        p5 = dist.ppf(0.05)
        p95 = dist.ppf(0.95)
        spread = p95 - p5
        range_span = max_value - min_value

        if coverage >= target_coverage and spread >= min_spread_ratio * range_span:
            return dist

    return None  # No suitable distribution found

def generate_lognormal_value(dist, min_value, max_value, fallback_value=None, max_tries=1000):
    """
    Samples from the given log-normal distribution and ensures the value is within bounds.
    """
    for _ in range(max_tries):
        val = dist.rvs()
        if min_value <= val <= max_value:
            return val
    return fallback_value if fallback_value is not None else (min_value + max_value) / 2

def generate_powerlaw_value(alpha, min_value, max_value):
    """
    Generates a power-law distributed random value between min_value and max_value.

    Parameters:
        alpha (float): The exponent (α > 1 for heavy-tailed).
        min_value (float): Minimum possible value.
        max_value (float): Maximum possible value.

    Returns:
        float: Random sample from the bounded power-law distribution.
    """
    assert alpha > 1, "Alpha must be > 1 for a heavy-tailed power-law."
    assert max_value > min_value > 0, "Bounds must be positive and min < max."

    # Inverse transform sampling with bounded support
    r = np.random.uniform(0, 1)
    min_pow = min_value ** (1 - alpha)
    max_pow = max_value ** (1 - alpha)
    x = (min_pow - r * (min_pow - max_pow)) ** (1 / (1 - alpha))

    return x