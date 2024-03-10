import os
import random


def get_random_string():
    len = 6
    charset = 'abcdefghijklmnopqrstuvwxyz0123456789'
    random_string = ''.join(random.choices(charset, k=len))
    return random_string