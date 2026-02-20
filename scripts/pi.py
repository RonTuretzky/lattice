#!/usr/bin/env python3
"""Compute Pi to 20 decimal places. LAT-174 process validation."""

from decimal import Decimal, getcontext

# Set precision high enough to get 20 accurate digits
getcontext().prec = 50


def compute_pi() -> Decimal:
    """Compute Pi using the Chudnovsky algorithm."""
    getcontext().prec = 50

    C = 426880 * Decimal(10005).sqrt()
    S = Decimal(0)

    for k in range(20):
        num = factorial(6 * k) * (13591409 + 545140134 * k)
        den = factorial(3 * k) * factorial(k) ** 3 * (-262537412640768000) ** k
        S += Decimal(num) / Decimal(den)

    return C / S


def factorial(n: int) -> int:
    """Compute factorial."""
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


pi = compute_pi()
# Truncate to 20 decimal places
pi_str = str(pi)[:22]  # "3." + 20 digits
print(pi_str)
