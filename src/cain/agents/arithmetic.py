"""Bounded literal arithmetic; never eval, names, calls or generated code."""
import ast
from fractions import Fraction
import operator
import re


def answer(payload: str) -> str:
    expression = re.sub(r'^.*?(?:quanto\s+(?:é|e|dá|da)|calcule|calcular|what is)\s+',
                        '', payload.strip(), count=1, flags=re.I)
    expression = expression.rstrip('?! .').replace('−', '-').replace('–', '-').replace(',', '.')
    operations = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
                  ast.Div: operator.truediv, ast.Mod: operator.mod}
    try:
        if len(expression) > 160:
            raise ValueError('expression limit')
        tree = ast.parse(expression, mode='eval')
        if sum(1 for _ in ast.walk(tree)) > 64:
            raise ValueError('node limit')

        def value(node):
            if isinstance(node, ast.Constant) and type(node.value) in (int, float):
                result = Fraction(str(node.value))
            elif isinstance(node, ast.UnaryOp) and type(node.op) in (ast.UAdd, ast.USub):
                result = value(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
            elif isinstance(node, ast.BinOp) and type(node.op) in operations:
                result = operations[type(node.op)](value(node.left), value(node.right))
            else:
                raise ValueError('unsupported expression')
            if max(abs(result.numerator), result.denominator) > 10**18:
                raise ValueError('numeric limit')
            return result

        return f'{expression} = {value(tree.body)}.'
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError, RecursionError):
        return ('Não foi possível calcular esta expressão com segurança. Use números finitos, '
                'parênteses e +, -, *, / ou %; divisão por zero não é definida.')
