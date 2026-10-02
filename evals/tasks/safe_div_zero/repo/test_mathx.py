from mathx import safe_div

def test_zero_returns_none():
    assert safe_div(1, 0) is None

def test_normal_division():
    assert safe_div(9, 3) == 3
