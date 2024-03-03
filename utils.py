import random


def generate_token(length):
    base = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ123456789-+="
    return "".join([random.choice(base) for _ in range(length)])


def calculate_size(size: int):
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_iteration = 0
    calculated_size = size

    while calculated_size >= 1024:
        calculated_size /= 1024
        unit_iteration += 1

    return f"{round(calculated_size, 2)}{units[unit_iteration]}"
