def paginate(items, page, size):
    """Return the items on a 1-based page."""
    start = (page - 1) * size
    return items[start:start + size]
