# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import logging
from typing import Iterator, Optional, Sequence, Tuple, Union

from . import exceptions

logger = logging.getLogger(__name__)


def to_unicode(s: Union[bytes, str]) -> str:
    if isinstance(s, bytes):
        try:
            return s.decode("ascii")
        except UnicodeDecodeError:
            logger.warning(
                "An error occurred while decoding %s in ASCII 'strict' mode. Fallback to "
                "'ignore' errors handling, some characters might have been stripped",
                s,
            )
            return s.decode("ascii", "ignore")
    return s


class SequenceSet:
    """Tests membership of one or more sequence sets.

    *highest_id* is the value of * and must be supplied for sets using it.
    """

    def __init__(
        self,
        sequence_sets: Union[bytes, str, int, Sequence[Union[bytes, str, int]]],
        highest_id: bytes = b"*",
    ):
        if isinstance(sequence_sets, (int, str, bytes)):
            sequence_sets = (sequence_sets,)
        self._id_ranges = [
            id_range
            for sequence_set in sequence_sets
            for id_range in SequenceSet._to_ranges(sequence_set, highest_id)
        ]

    @staticmethod
    def _to_ranges(sequence_set: Union[bytes, str, int], highest_id: bytes):
        if isinstance(sequence_set, int):
            return (range(sequence_set, sequence_set + 1),)
        return (
            SequenceSet._to_range(r, highest_id)
            for r in to_bytes(sequence_set).split(b",")
        )

    @staticmethod
    def _to_range(sequence: bytes, highest_id: bytes):
        first, colon, second = sequence.replace(b"*", highest_id).partition(b":")
        first = int(first)
        if colon:
            second = int(second)
            return range(min(first, second), max(first, second) + 1)
        else:
            return range(first, first + 1)

    def __contains__(self, message_id: int):
        return any(message_id in id_range for id_range in self._id_ranges)


def to_bytes(s: Union[bytes, str], charset: str = "ascii") -> bytes:
    if isinstance(s, str):
        return s.encode(charset)
    return s


def assert_imap_protocol(condition: bool, message: Optional[bytes] = None) -> None:
    if not condition:
        msg = "Server replied with a response that violates the IMAP protocol"
        if message:
            # FIXME(jlvillal): This looks wrong as it repeats `msg` twice
            msg += "{}: {}".format(
                msg, message.decode(encoding="ascii", errors="ignore")
            )
        raise exceptions.ProtocolError(msg)


_TupleAtomPart = Union[None, int, bytes]
_TupleAtom = Tuple[Union[_TupleAtomPart, "_TupleAtom"], ...]


def chunk(lst: _TupleAtom, size: int) -> Iterator[_TupleAtom]:
    for i in range(0, len(lst), size):
        yield lst[i : i + size]
