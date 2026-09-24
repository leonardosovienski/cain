"""JSON Canonicalization Scheme (RFC 8785) for the memory event log.

Keys are sorted by UTF-16 code units, strings use the ECMAScript JSON escaping, and numbers
use the ECMAScript shortest round-trip form. Input outside I-JSON (non-finite numbers,
integers beyond 2**53, lone surrogates, non-string keys) is rejected instead of normalized.
"""

from decimal import Decimal
import json
import math

MAX_SAFE_INTEGER = 2**53


class CanonicalizationError(ValueError):
    pass


def _number(value) -> str:
    if type(value) is int:
        if abs(value) > MAX_SAFE_INTEGER:
            raise CanonicalizationError("integer outside the IEEE-754 exact range")
        return str(value)
    if not math.isfinite(value):
        raise CanonicalizationError("non-finite number")
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    # repr() is the shortest round-trip decimal; Decimal exposes its digits and exponent.
    digits_tuple, exponent = Decimal(repr(abs(value))).as_tuple()[1:]
    digits = "".join(map(str, digits_tuple)).lstrip("0") or "0"
    trailing = len(digits) - len(digits.rstrip("0"))
    digits, exponent = digits.rstrip("0") or "0", exponent + trailing
    k = len(digits)
    n = exponent + k  # value = 0.digits x 10**n
    if k <= n <= 21:
        text = digits + "0" * (n - k)
    elif 0 < n <= 21:
        text = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        text = "0." + "0" * (-n) + digits
    else:
        mantissa = digits if k == 1 else digits[0] + "." + digits[1:]
        text = f"{mantissa}e{'+' if n - 1 >= 0 else '-'}{abs(n - 1)}"
    return sign + text


def _string(value: str) -> str:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise CanonicalizationError("lone surrogate in string") from exc
    return json.dumps(value, ensure_ascii=False)


def _serialize(value, out: list[str]) -> None:
    if value is None:
        out.append("null")
    elif value is True:
        out.append("true")
    elif value is False:
        out.append("false")
    elif type(value) in (int, float):
        out.append(_number(value))
    elif type(value) is str:
        out.append(_string(value))
    elif type(value) in (list, tuple):
        out.append("[")
        for index, item in enumerate(value):
            if index:
                out.append(",")
            _serialize(item, out)
        out.append("]")
    elif type(value) is dict:
        if any(type(key) is not str for key in value):
            raise CanonicalizationError("object keys must be strings")
        out.append("{")
        for index, key in enumerate(sorted(value, key=lambda k: k.encode("utf-16-be", "surrogatepass"))):
            if index:
                out.append(",")
            out.append(_string(key))
            out.append(":")
            _serialize(value[key], out)
        out.append("}")
    else:
        raise CanonicalizationError(f"unsupported JSON value {type(value).__name__}")


def canonicalize(value) -> bytes:
    out: list[str] = []
    _serialize(value, out)
    return "".join(out).encode("utf-8")
