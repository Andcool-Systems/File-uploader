import random

def generate_token(length):
    base = "abcdefghijklmnopqrstuvwxyz123456789-+="
    return "".join([random.choice(base) for x in range(length)])

