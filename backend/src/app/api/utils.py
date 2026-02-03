import re

_digits = re.compile(r"\D+")


def only_digits(value: str | None) -> str:
    return _digits.sub("", value or "")
