import pandas as pd
import numpy as np


def clients_intersection(clients_prev, clients):
    """
    Calculate the intersection of two sets of clients.
    """
    return len(clients_prev & clients)


def clients_new(clients_prev, clients):
    """
    Calculate the new clients.
    """
    return len(clients - clients_prev)


clients_intersection_vectorized = np.vectorize(clients_intersection)
clients_new_vectorized = np.vectorize(clients_new)
