"""
This module contains a handful of simple parser combinators to make parsing complex IRC commands more palatable.
All the functions in this module return a pair of (parsed, leftover)
"""

from typing import Callable, Optional, Tuple, TypeVar, Iterable


class ParseError(Exception):
    "An error encountered while attempting to parse input"
    pass


def text(input: bytes) -> Tuple[bytes, bytes]:
    "Parse one sequence of text, defined as a whitespace-terminated sequence of any character at all"
    word_end = input.find(b" ")
    word_end = word_end if word_end >= 0 else len(input)
    return input[:word_end], input[word_end:]


def whitespace(input: bytes) -> Tuple[None, bytes]:
    "Strip whitespace from the input"
    return None, input.strip()


def char(input: bytes, char: bytes) -> Tuple[None, bytes]:
    "Assert that the input begins with the specified character and remove it"
    if not input.startswith(char):
        raise ParseError
    else:
        return None, input[1:]


def one_of(input: bytes, options: Iterable[bytes]) -> Tuple[bytes, bytes]:
    "Assert that the input begins with one of the specified characters, remove it, and return which character it was as well"
    for option in options:
        if input.startswith(option):
            return option, input[len(option):]
    raise ParseError


T = TypeVar("T")


def optional(input: bytes, parser: Callable[[bytes], Tuple[T, bytes]]) -> Tuple[Optional[T], bytes]:
    """
    Try to run the specified parser. If it succeeds, return its result. 
    If it fails, return `None` plus all the input, unchanged"
    """
    try:
        return parser(input)
    except ParseError:
        return None, input
