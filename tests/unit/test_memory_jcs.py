"""RFC 8785 (JCS) vectors for the memory event log canonicalization."""

import math

import pytest

from cain.memory.jcs import CanonicalizationError, canonicalize


def test_rfc8785_section_3_2_2_sample():
    value = {
        "numbers": [333333333.33333329, 1e30, 4.50, 2e-3, 0.000000000000000000000000001],
        "string": "".join(map(chr, [0x20AC, 0x24, 0x0F, 0x0A, 0x41, 0x27, 0x42, 0x22, 0x5C, 0x5C, 0x22, 0x2F])),
        "literals": [None, True, False],
    }
    expected = (
        '{"literals":[null,true,false],"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],'
        '"string":"€$\\u000f\\nA\'B\\"\\\\\\\\\\"/"}'
    )
    assert canonicalize(value).decode("utf-8") == expected


def test_rfc8785_key_order_is_utf16_code_units():
    value = {"€": "Euro Sign", "\r": "Carriage Return", "דּ": "Hebrew Letter Dalet With Dagesh",
             "1": "One", "\U0001F600": "Emoji: Grinning Face", "\u0080": "Control",
             "ö": "Latin Small Letter O With Diaeresis"}
    keys = list(__import__("json").loads(canonicalize(value)))
    assert keys == ["\r", "1", "\u0080", "ö", "€", "\U0001F600", "דּ"]


@pytest.mark.parametrize("number,text", [
    (0.0, "0"), (-0.0, "0"), (1e21, "1e+21"), (1e20, "100000000000000000000"), (1e-7, "1e-7"),
    (0.000001, "0.000001"), (5e-324, "5e-324"), (1.7976931348623157e308, "1.7976931348623157e+308"),
    (2.0, "2"), (100.0, "100"), (-1.5, "-1.5"), (123456789012345680000.0, "123456789012345680000"),
    (9007199254740992, "9007199254740992"), (-9007199254740992, "-9007199254740992"), (7, "7"),
])
def test_ecmascript_number_serialization(number, text):
    assert canonicalize(number).decode() == text


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, 2**53 + 1, "\ud800", {1: "x"}, {"a": {1, 2}}])
def test_outside_i_json_is_rejected(bad):
    with pytest.raises(CanonicalizationError):
        canonicalize(bad)


def test_nested_and_tuple():
    assert canonicalize({"b": [1, {"d": None, "c": "é"}], "a": (True,)}) == '{"a":[true],"b":[1,{"c":"é","d":null}]}'.encode()
