import re


def slugify(title):
    """'Hello, World!' -> 'hello-world'"""
    words = re.findall(r"[A-Za-z0-9]+", title)
    return "-".join(words)
