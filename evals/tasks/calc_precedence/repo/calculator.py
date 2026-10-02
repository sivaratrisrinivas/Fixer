class Calculator:
    def __init__(self):
        self.operators = {
            "+": lambda a, b: a + b,
            "-": lambda a, b: a - b,
            "*": lambda a, b: a * b,
            "/": lambda a, b: a / b,
        }
        self.precedence = {"+": 1, "-": 1, "*": 1, "/": 2}

    def evaluate(self, expression):
        tokens = expression.split()
        values, ops = [], []
        for token in tokens:
            if token in self.operators:
                while ops and self.precedence[ops[-1]] >= self.precedence[token]:
                    self._apply(ops, values)
                ops.append(token)
            else:
                values.append(float(token))
        while ops:
            self._apply(ops, values)
        return values[0]

    def _apply(self, ops, values):
        op = ops.pop()
        b, a = values.pop(), values.pop()
        values.append(self.operators[op](a, b))
