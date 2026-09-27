"""Brazilian CPF validation (check digits). Format is 11 digits."""

import re


def digits_only(cpf: str) -> str:
    return re.sub(r"\D", "", cpf or "")


def validate_cpf(cpf: str) -> bool:
    """Return True when `cpf` has a valid check-digit sequence.

    Accepts formatted input like ``123.456.789-00``; compares digits only.
    """
    digits = digits_only(cpf)
    if len(digits) != 11 or digits == digits[0] * 11:
        return False
    for length in (9, 10):
        total = sum(
            int(d) * w for d, w in zip(digits[:length], range(length + 1, 1, -1), strict=True)
        )
        check = 0 if total % 11 < 2 else 11 - total % 11
        if int(digits[length]) != check:
            return False
    return True
