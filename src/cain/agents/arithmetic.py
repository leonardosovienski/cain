"""Bounded literal arithmetic; never eval, names, calls or generated code."""
import ast
from fractions import Fraction
import operator
import re


def sequence_request(payload: str):
    """Parse a complete bounded sequence of literal numeric operations, or abstain.

    This grammar never consumes a prefix of an unrelated instruction. Names,
    external facts, code and an additional task are not arithmetic operands.
    """
    if len(payload) > 1200:
        return None
    number = r"[+-]?\d{1,15}(?:[.,]\d{1,9})?"
    start = re.match(r"\s*(?:comece|inicie)\s+com\s+(" + number + r")", payload, re.I)
    if not start:
        return None
    tail = payload[start.end():]
    only = re.search(
        r"[.!?]\s*(?:responda|retorne)\s+(?:apenas|somente)\s+"
        r"(?:com\s+)?o\s+(?:resultado|número|numero)\s*[.!?]?\s*$", tail, re.I,
    )
    if only:
        tail = tail[:only.start()]
    tail = tail.rstrip(" .!?")
    operation = re.compile(
        r"\s*(?:[,;]\s*(?:e\s+)?|e\s+)(some|adicione|subtraia|multiplique\s+por|divida\s+por)"
        r"\s+(" + number + r")", re.I,
    )
    operations = []
    offset = 0
    while offset < len(tail):
        match = operation.match(tail, offset)
        if not match or len(operations) >= 16:
            return None
        operations.append((match[1].lower(), match[2].replace(",", ".")))
        offset = match.end()
    return (start[1].replace(",", "."), operations, bool(only)) if operations else None


def answer(payload: str) -> str:
    sequence = sequence_request(payload)
    if sequence is not None:
        initial, steps, only = sequence
        result = Fraction(initial)
        try:
            for operation, operand in steps:
                value = Fraction(operand)
                if operation in {"some", "adicione"}:
                    result += value
                elif operation == "subtraia":
                    result -= value
                elif operation.startswith("multiplique"):
                    result *= value
                else:
                    result /= value
                if max(abs(result.numerator), result.denominator) > 10**18:
                    raise ValueError("numeric limit")
            return str(result) if only else f"Resultado: {result}."
        except (ValueError, ZeroDivisionError):
            return "Não foi possível calcular: divisão por zero ou limite numérico excedido."
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
                # AST float values have already rounded. Parse the original
                # decimal token, with a bounded grammar before constructing it.
                literal = ast.get_source_segment(expression, node)
                if literal is None or not re.fullmatch(r'(?:\d+(?:\.\d*)?|\.\d+)', literal):
                    raise ValueError('only decimal literals supported')
                result = Fraction(literal)
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
