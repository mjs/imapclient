# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import pytest

from imapclient.response_lexer import TokenSource


def _check(text_in, expected_out):
    tokens = TokenSource(text_in)
    assert list(tokens) == expected_out


def _check_error(text_in, expected_message):
    with pytest.raises(ValueError, match=expected_message):
        list(TokenSource(text_in))


def test_one_token():
    _check([b"abc"], [b"abc"])


def test_simple_tokens():
    _check([b"abc 111 def"], [b"abc", b"111", b"def"])


def test_multiple_inputs():
    _check([b"abc 111", b"def 222"], [b"abc", b"111", b"def", b"222"])


def test_whitespace():
    _check([b"abc   def"], [b"abc", b"def"])
    _check([b"  abc \t\t\r\r\n\n  def  "], [b"abc", b"def"])


def test_quoted_strings():
    _check([b'"abc def"'], [b'"abc def"'])
    _check([b'""'], [b'""'])
    _check([b'111 "abc def" 222'], [b"111", b'"abc def"', b"222"])


def test_unterminated_strings():
    message = "No closing '\"'"
    _check_error([b'"'], message)
    _check_error([b'"aaa bbb'], message)


def test_escaping():
    _check([rb'"aaa\"bbb"'], [rb'"aaa"bbb"'])
    _check([rb'"aaa\\bbb"'], [rb'"aaa\bbb"'])
    _check([rb'"aaa\\bbb \"\""'], [rb'"aaa\bbb """'])


def test_invalid_escape():
    _check([rb'"aaa\Zbbb"'], [rb'"aaa\Zbbb"'])


def test_lists():
    _check([b"()"], [b"(", b")"])
    _check([b"(aaa)"], [b"(", b"aaa", b")"])
    _check([b'(aaa "bbb def"   123)'], [b"(", b"aaa", b'"bbb def"', b"123", b")"])
    _check([b"(aaa)(bbb ccc)"], [b"(", b"aaa", b")", b"(", b"bbb", b"ccc", b")"])
    _check([b"(aaa (bbb ccc))"], [b"(", b"aaa", b"(", b"bbb", b"ccc", b")", b")"])


def test_square_brackets():
    _check([b"[aaa bbb]"], [b"[aaa bbb]"])
    _check([b"aaa[bbb]"], [b"aaa[bbb]"])
    _check([b"[bbb]aaa"], [b"[bbb]aaa"])
    _check([b"aaa [bbb]"], [b"aaa", b"[bbb]"])


def test_no_escaping_in_square_brackets():
    _check([rb"[aaa\\bbb]"], [rb"[aaa\\bbb]"])


def test_unmatched_square_brackets():
    message = "No closing ']'"
    _check_error([b"["], message)
    _check_error([b"[aaa bbb"], message)


def test_literal():
    source = TokenSource([(b"abc {7}", b"foo bar"), b")"])
    tokens = iter(source)
    assert next(tokens) == b"abc"
    assert next(tokens) == b"{7}"
    assert source.current_literal == b"foo bar"
    assert next(tokens) == b")"
    with pytest.raises(StopIteration):
        next(tokens)


def test_literals():
    source = TokenSource([(b"abc {7}", b"foo bar"), (b"{5}", b"snafu"), b")"])
    tokens = iter(source)
    assert next(tokens) == b"abc"
    assert next(tokens) == b"{7}"
    assert source.current_literal == b"foo bar"
    assert next(tokens) == b"{5}"
    assert source.current_literal == b"snafu"
    assert next(tokens) == b")"
    with pytest.raises(StopIteration):
        next(tokens)
