# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from six import next

from imapclient.response_lexer import TokenSource
from imapclient.test.util import unittest


class TestTokenSource(unittest.TestCase):

    def test_one_token(self):
        self.check([b'abc'],
                   [b'abc'])

    def test_simple_tokens(self):
        self.check([b'abc 111 def'],
                   [b'abc', b'111', b'def'])

    def test_multiple_inputs(self):
        self.check([b'abc 111', b'def 222'],
                   [b'abc', b'111', b'def', b'222'])

    def test_whitespace(self):
        self.check([b'abc   def'],
                   [b'abc', b'def'])
        self.check([b'  abc \t\t\r\r\n\n  def  '],
                   [b'abc', b'def'])

    def test_quoted_strings(self):
        self.check([b'"abc def"'],
                   [b'"abc def"'])
        self.check([b'""'],
                   [b'""'])
        self.check([b'111 "abc def" 222'],
                   [b'111', b'"abc def"', b'222'])

    def test_unterminated_strings(self):
        message = "No closing '\"'"
        self.check_error([b'"'], message)
        self.check_error([b'"aaa bbb'], message)

    def test_escaping(self):
        self.check([br'"aaa\"bbb"'],
                   [br'"aaa"bbb"'])
        self.check([br'"aaa\\bbb"'],
                   [br'"aaa\bbb"'])
        self.check([br'"aaa\\bbb \"\""'],
                   [br'"aaa\bbb """'])

    def test_invalid_escape(self):
        self.check([br'"aaa\Zbbb"'],
                   [br'"aaa\Zbbb"'])

    def test_lists(self):
        self.check([b'()'],
                   [b'(', b')'])
        self.check([b'(aaa)'],
                   [b'(', b'aaa', b')'])
        self.check([b'(aaa "bbb def"   123)'],
                   [b'(', b'aaa', b'"bbb def"', b'123', b')'])
        self.check([b'(aaa)(bbb ccc)'],
                   [b'(', b'aaa', b')', b'(', b'bbb', b'ccc', b')'])
        self.check([b'(aaa (bbb ccc))'],
                   [b'(', b'aaa', b'(', b'bbb', b'ccc', b')', b')'])

    def test_square_brackets(self):
        self.check([b'[aaa bbb]'],
                   [b'[aaa bbb]'])
        self.check([b'aaa[bbb]'],
                   [b'aaa[bbb]'])
        self.check([b'[bbb]aaa'],
                   [b'[bbb]aaa'])
        self.check([b'aaa [bbb]'],
                   [b'aaa', b'[bbb]'])

    def test_no_escaping_in_square_brackets(self):
        self.check([br'[aaa\\bbb]'],
                   [br'[aaa\\bbb]'])

    def test_unmatched_square_brackets(self):
        message = "No closing ']'"
        self.check_error([b'['], message)
        self.check_error([b'[aaa bbb'], message)

    def test_literal(self):
        source = TokenSource([(b'abc {7}', b'foo bar'), b')'])
        tokens = iter(source)
        self.assertEqual(next(tokens), b'abc')
        self.assertEqual(next(tokens), b'{7}')
        self.assertEqual(source.current_literal, b'foo bar')
        self.assertEqual(next(tokens), b')')
        self.assertRaises(StopIteration, lambda: next(tokens))

    def test_literals(self):
        source = TokenSource([
            (b'abc {7}', b'foo bar'),
            (b'{5}', b'snafu'),
            b')'])
        tokens = iter(source)
        self.assertEqual(next(tokens), b'abc')
        self.assertEqual(next(tokens), b'{7}')
        self.assertEqual(source.current_literal, b'foo bar')
        self.assertEqual(next(tokens), b'{5}')
        self.assertEqual(source.current_literal, b'snafu')
        self.assertEqual(next(tokens), b')')
        self.assertRaises(StopIteration, lambda: next(tokens))

    def check(self, text_in, expected_out):
        tokens = TokenSource(text_in)
        self.assertSequenceEqual(list(tokens), expected_out)

    def check_error(self, text_in, expected_message):
        self.assertRaisesRegex(ValueError, expected_message,
                               lambda: list(TokenSource(text_in)))
