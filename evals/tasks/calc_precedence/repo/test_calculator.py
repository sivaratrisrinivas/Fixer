from calculator import Calculator

def test_precedence():
    assert Calculator().evaluate("3 + 7 * 2") == 17

def test_left_to_right():
    assert Calculator().evaluate("8 / 2 * 3") == 12

def test_simple():
    assert Calculator().evaluate("10 - 4") == 6
