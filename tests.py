import unittest

class DummyTests(unittest.TestCase):
    def test_one(self):
        self.assertEqual(1, 1)
    def test_two(self):
        self.assertEqual(2, 2)
    def test_three(self):
        self.assertEqual(3, 3)
    def test_four(self):
        self.assertEqual(4, 4)
    def test_five(self):
        self.assertEqual(5, 5)
    def test_six(self):
        self.assertEqual(6, 6)
    def test_seven(self):
        self.assertEqual(7, 7)
    def test_eight(self):
        self.assertEqual(8, 8)
    def test_nine(self):
        self.assertEqual(9, 9)

if __name__ == '__main__':
    unittest.main()