"""Minimal three-valued finite-trace checks; not a novel temporal logic.

Inputs must be observed booleans or None (unavailable). Intervals are inclusive.
This module never interprets natural language, accesses hidden benchmark labels,
mutates state, or promotes an unknown result to success.
"""
from collections.abc import Sequence

def _values(values):
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise TypeError('Expected a sequence of booleans or None')
    if any(v is not None and type(v) is not bool for v in values):
        raise TypeError('Only observed boolean values or None are permitted')

def verdict(values, mode, start=0, end=None):
    _values(values)
    if not values: raise ValueError('An observed trace cannot be empty')
    if mode not in ('eventually','terminal','always'):
        raise ValueError('Unsupported obligation mode')
    if end is None: end = len(values)-1
    if type(start) is not int or type(end) is not int:
        raise TypeError('Interval endpoints must be integers, not booleans')
    if not (0 <= start <= end < len(values)):
        raise ValueError('Invalid or unavailable interval')
    v = values[start:end+1]
    if mode == 'terminal': return v[-1]
    if mode == 'eventually':
        if any(x is True for x in v): return True
        return None if any(x is None for x in v) else False
    if any(x is False for x in v): return False
    return None if any(x is None for x in v) else True

def combine(values):
    _values(values)
    if not values: return None
    if any(v is False for v in values): return False
    return None if any(v is None for v in values) else True
