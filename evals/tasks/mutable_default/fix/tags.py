def add_tag(tag, tags=None):
    """Return a new list with tag appended."""
    return [*(tags or []), tag]
