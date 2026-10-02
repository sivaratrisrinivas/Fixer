from text_utils import slugify

def test_lowercase():
    assert slugify("Hello, World!") == "hello-world"

def test_numbers_kept():
    assert slugify("Top 10 Tips") == "top-10-tips"

def test_empty():
    assert slugify("!!!") == ""
