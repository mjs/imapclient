# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from imapclient.response_lexer import TokenSource
from imapclient.six import next
from imapclient.test.util import unittest


class TestTokenSource(unittest.TestCase):

    def test_one_token(self):
        self.check(['abc'],
                   ['abc'])

    def test_simple_tokens(self):
        self.check(['abc 111 def'],
                   ['abc', '111', 'def'])

    def test_multiple_inputs(self):
        self.check(['abc 111', 'def 222'],
                   ['abc', '111', 'def', '222'])

    def test_whitespace(self):
        self.check(['abc   def'],
                   ['abc', 'def'])
        self.check(['  abc \t\t\r\r\n\n  def  '],
                   ['abc', 'def'])

    def test_quoted_strings(self):
         self.check(['"abc def"'],
                    ['"abc def"'])
         self.check(['""'],
                    ['""'])
         self.check(['111 "abc def" 222'],
                    ['111', '"abc def"', '222'])

    def test_unterminated_strings(self):
        message = "No closing '\"'"
        self.check_error(['"'], message)
        self.check_error(['"aaa bbb'], message)

    def test_escaping(self):
         self.check([r'"aaa\"bbb"'],
                    [r'"aaa"bbb"'])
         self.check([r'"aaa\\bbb"'],
                    [r'"aaa\bbb"'])
         self.check([r'"aaa\\bbb \"\""'],
                    [r'"aaa\bbb """'])

    def test_invalid_escape(self):
         self.check([r'"aaa\Zbbb"'],
                    [r'"aaa\Zbbb"'])

    def test_lists(self):
         self.check(['()'],
                    ['(', ')'])
         self.check(['(aaa)'],
                    ['(', 'aaa', ')'])
         self.check(['(aaa "bbb def"   123)'],
                    ['(', 'aaa', '"bbb def"', '123', ')'])
         self.check(['(aaa)(bbb ccc)'],
                    ['(', 'aaa', ')', '(', 'bbb', 'ccc', ')'])
         self.check(['(aaa (bbb ccc))'],
                    ['(', 'aaa', '(', 'bbb', 'ccc', ')', ')'])

    def test_square_brackets(self):
        self.check(['[aaa bbb]'],
                   ['[aaa bbb]'])
        self.check(['aaa[bbb]'],
                   ['aaa[bbb]'])
        self.check(['[bbb]aaa'],
                   ['[bbb]aaa'])
        self.check(['aaa [bbb]'],
                   ['aaa', '[bbb]'])

    def test_no_escaping_in_square_brackets(self):
        self.check([r'[aaa\\bbb]'],
                   [r'[aaa\\bbb]'])

    def test_unmatched_square_brackets(self):
        message = "No closing ']'"
        self.check_error(['['], message)
        self.check_error(['[aaa bbb'], message)

    def test_literal(self):
        source = TokenSource([('abc {7}', 'foo bar'), ')'])
        tokens = iter(source)
        self.assertEqual(next(tokens), 'abc')
        self.assertEqual(next(tokens), '{7}')
        self.assertEqual(source.current_literal, 'foo bar')
        self.assertEqual(next(tokens), ')')
        self.assertRaises(StopIteration, lambda: next(tokens))

    def test_literals(self):
        source = TokenSource([
            ('abc {7}', 'foo bar'),
            ('{5}', 'snafu'),
            ')'])
        tokens = iter(source)
        self.assertEqual(next(tokens), 'abc')
        self.assertEqual(next(tokens), '{7}')
        self.assertEqual(source.current_literal, 'foo bar')
        self.assertEqual(next(tokens), '{5}')
        self.assertEqual(source.current_literal, 'snafu')
        self.assertEqual(next(tokens), ')')
        self.assertRaises(StopIteration, lambda: next(tokens))

    def check(self, text_in, expected_out):
        tokens = TokenSource(text_in)
        self.assertSequenceEqual(list(tokens), expected_out)

    def check_error(self, text_in, expected_message):
        self.assertRaisesRegex(ValueError, expected_message,
                               lambda: list(TokenSource(text_in)))
