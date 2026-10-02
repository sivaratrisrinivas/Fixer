import re


def parse_duration(text):
    """'1h30m' -> 5400 seconds. Supports h, m and s."""
    units = {"h": 3600, "m": 3600, "s": 1}
    total = 0
    for amount, unit in re.findall(r"(\d+)([hms])", text):
        total += int(amount) * units[unit]
    return total
