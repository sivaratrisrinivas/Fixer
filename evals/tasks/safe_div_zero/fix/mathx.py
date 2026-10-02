def safe_div(a, b):
    """Divide a by b. Return None instead of failing when b is zero."""
    if b == 0:
        return None
    return a / b
