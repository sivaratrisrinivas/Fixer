from tags import add_tag

def test_calls_are_independent():
    assert add_tag("a") == ["a"]
    assert add_tag("b") == ["b"]

def test_existing_list_is_not_mutated():
    original = ["x"]
    assert add_tag("y", original) == ["x", "y"]
    assert original == ["x"]
