import unittest
from calculator.pkg.calculator import Calculator

class CalculatorTests(unittest.TestCase):
    def test_addition(self):
        calc = Calculator()
        self.assertEqual(calc.evaluate("3 + 7 * 2"), 17)

if __name__ == '__main__':
    unittest.main()