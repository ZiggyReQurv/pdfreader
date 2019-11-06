import logging

from decimal import Decimal

from ..constants import DEFAULT_ENCODING
from ..filters import apply_filter
from ..utils import cached_property


null = None
Boolean = bool
Integer = int
Real = Decimal
Array = list
Dictionary = dict


class String(bytes):
    """ A string object shall consist of a series of zero or more bytes """


class Name(str):
    """ Name type: /SomeName """


class HexString(str):
    """ Hexadecimal string: <AF20FA> """

    @property
    def as_int(self):
        return int(self, 16)

    def to_string(self):
        return self.to_bytes().decode(DEFAULT_ENCODING)

    def to_bytes(self):
        return bytes.fromhex(self)


class Stream(object):
    """ binary stream: dictionary and binary data
        common keys:
        Length - integer (required)
        Filter - name or array
        DecodeParams - dict or array
        F - file specification

    """

    def __init__(self, info_dict, binary_stream):
        assert isinstance(info_dict, Dictionary)
        assert isinstance(binary_stream, bytes)

        if "Length" not in info_dict:
            raise KeyError("Missing stream length")

        if info_dict["Length"] != len(binary_stream):
            raise ValueError("Inconsistend stream")

        self.dictionary = info_dict
        self.stream = binary_stream

    def __getitem__(self, item):
        return self.dictionary.__getitem__(item)

    def get(self, item, default=None):
        return self.dictionary.get(item, default)

    def __len__(self):
        return len(self.stream)

    def __repr__(self):
        data = self.stream
        if len(data) > 25:
            data = (self.stream[:25] + b' ...')
        return "<Stream:len={},data={}>".format(self.dictionary["Length"], repr(data))

    def type(self):
        return self.get('Type')

    @cached_property
    def filtered(self):
        filters = self.get('Filter')
        if not filters:
            return self.stream

        if isinstance(filters, Array):
            farr = filters
        elif isinstance(filters, Name):
            farr = Array()
            farr.append(filters)
        else:
            raise TypeError("Incorrect filter type: {}".format(filters))

        binary = self.stream
        filters_applied = []
        for fname in farr:
            try:
                binary = apply_filter(fname, binary, self.dictionary.get("DecodeParams"))
                filters_applied.append(fname)
            except NotImplementedError:
                logging.exception("Leaving partially decoded. Filters applied: {}".format(filters_applied))
                break

        return binary

    def __eq__(self, other):
        return self.dictionary == other.dictionary and self.stream == other.stream

    @classmethod
    def from_stream(cls, other):
        return cls(other.dictionary, other.stream)

    def __getattr__(self, item):
        return self.dictionary.get(item)


class Comment(str):
    """ % Some PDF Comment """


class IndirectReference(object):
    def __init__(self, number, generation):
        """ 10 0 R """
        assert isinstance(number, int)
        assert isinstance(generation, int) and generation >= 0

        self.num = number
        self.gen = generation

    def __repr__(self):
        return "<IndirectReference:n={self.num},g={self.gen}>".format(self=self)

    def __eq__(self, other):
        return self.num == other.num and self.gen == other.gen


class IndirectObject(object):
    """ 10 0 obj
        ....
        endobj
    """
    def __init__(self, number, generation, value):
        assert isinstance(number, int)
        assert isinstance(generation, int) and generation >= 0
        assert isinstance(value,
                          (type(null), Boolean, Integer, Real, Array, Dictionary, String, Name, HexString, Stream,
                           IndirectReference))
        self.num = number
        self.gen = generation
        self.val = value

    @property
    def id(self):
        return self.num, self.gen

    def __repr__(self):
        return "<IndirectObject:n={self.num},g={self.gen},v={val}>".format(self=self, val=repr(self.val))

    def __eq__(self, other):
        return self.num == other.num and self.gen == other.gen


PDF_TYPES = (type(null), IndirectReference, IndirectObject, Comment, Stream, Dictionary, Integer, Real, Boolean, Array,
             String, HexString, Name)

ATOMIC_TYPES = (Integer, Real, Boolean, String, HexString, Name, type(null))


class Token(str):
    """ That's not a PDF type itself. We used it to reflect other than PDF types tokens.
        For example CMap: def, findresource, begin
    """
    pass


if __name__ == "__main__":
    import doctest
    doctest.testmod()
