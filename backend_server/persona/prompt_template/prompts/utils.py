"""
Shared utility functions for prompt modules.
"""
import random
import string


def get_random_alphanumeric(i=6, j=6):
    """
    Returns a random alpha numeric strength that has the length of somewhere
    between i and j.

    INPUT:
      i: min_range for the length
      j: max_range for the length
    OUTPUT:
      an alpha numeric str with the length of somewhere between i and j.
    """
    k = random.randint(i, j)
    x = ''.join(random.choices(string.ascii_letters + string.digits, k=k))
    return x
