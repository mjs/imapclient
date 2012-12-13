# Copyright (c) 2012, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

'''
Unit tests for the FetchTokeniser and FetchParser classes
'''

from datetime import datetime
from textwrap import dedent

from imapclient.fixed_offset import FixedOffset
from imapclient.response_parser import parse_response, parse_fetch_response, ParseError
from imapclient.six import b
from imapclient.test.util import unittest

#TODO: tokenising tests
#TODO: test invalid dates and times


CRLF = '\r\n'

class TestParseResponse(unittest.TestCase):

    def test_unquoted(self):
        self._test(b('FOO'), 'FOO')
        self._test(b('F.O:-O_0;'), 'F.O:-O_0;')
        self._test(b(r'\Seen'), r'\Seen')

    def test_string(self):
        self._test(b('"TEST"'), 'TEST')

    def test_int(self):
        self._test(b('45'), 45)

    def test_nil(self):
        self._test(b('NIL'), None)

    def test_empty_tuple(self):
        self._test(b('()'), ())

    def test_tuple(self):
        self._test(b('(123 "foo" GeE)'), (123, 'foo', 'GeE'))

    def test_int_and_tuple(self):
        self._test(b('1 (123 "foo")'), (1, (123, 'foo')), wrap=False)

    def test_nested_tuple(self):
        self._test(b('(123 "foo" ("more" NIL) 66)'),
                   (123, "foo", ("more", None), 66))

    def test_deeper_nest_tuple(self):
        self._test(b('(123 "foo" ((0 1 2) "more" NIL) 66)'),
                   (123, "foo", ((0, 1, 2), "more", None), 66))

    def test_complex_mixed(self):
        self._test(b('((FOO "PLAIN" ("CHARSET" "US-ASCII") NIL NIL "7BIT" 1152 23) '
                     '("TEXT" "PLAIN" ("CHARSET" "US-ASCII" "NAME" "cc.diff") '
                     '"<hi.there>" "foo" "BASE64" 4554 73) "MIXED")'),
                   (('FOO', 'PLAIN', ('CHARSET', 'US-ASCII'), None, None, '7BIT', 1152, 23),
                    ('TEXT', 'PLAIN', ('CHARSET', 'US-ASCII', 'NAME', 'cc.diff'),
                    '<hi.there>', 'foo', 'BASE64', 4554, 73), 'MIXED'))

    def test_envelopey(self):
        self._test(b('(UID 5 ENVELOPE ("internal_date" "subject" '
                     '(("name" NIL "address1" "domain1.com")) '
                     '((NIL NIL "address2" "domain2.com")) '
                     '(("name" NIL "address3" "domain3.com")) '
                     '((NIL NIL "address4" "domain4.com")) '
                     'NIL NIL "<reply-to-id>" "<msg_id>"))'),
                   ('UID',
                    5,
                    'ENVELOPE',
                    ('internal_date',
                     'subject',
                     (('name', None, 'address1', 'domain1.com'),),
                     ((None, None, 'address2', 'domain2.com'),),
                     (('name', None, 'address3', 'domain3.com'),),
                     ((None, None, 'address4', 'domain4.com'),),
                     None,
                     None,
                     '<reply-to-id>',
                     '<msg_id>')))

    def test_envelopey_quoted(self):
        self._test(b('(UID 5 ENVELOPE ("internal_date" "subject with \\"quotes\\"" '
                     '(("name" NIL "address1" "domain1.com")) '
                     '((NIL NIL "address2" "domain2.com")) '
                     '(("name" NIL "address3" "domain3.com")) '
                     '((NIL NIL "address4" "domain4.com")) '
                     'NIL NIL "<reply-to-id>" "<msg_id>"))'),
                   ('UID',
                    5,
                    'ENVELOPE',
                    ('internal_date',
                     'subject with "quotes"',
                     (('name', None, 'address1', 'domain1.com'),),
                     ((None, None, 'address2', 'domain2.com'),),
                     (('name', None, 'address3', 'domain3.com'),),
                     ((None, None, 'address4', 'domain4.com'),),
                     None,
                     None,
                     '<reply-to-id>',
                     '<msg_id>')))

    def test_literal(self):
        literal_text = add_crlf(dedent("""\
            012
            abc def XYZ
            """))
        self._test([(b('{18}'), b(literal_text))], literal_text)


    def test_literal_with_more(self):
        literal_text = add_crlf(dedent("""\
            012
            abc def XYZ
            """))
        response = [(b('(12 "foo" {18}'), b(literal_text)), b(")")]
        self._test(response, (12, 'foo', literal_text))


    def test_quoted_specials(self):
        self._test(b(r'"\"foo bar\""'), '"foo bar"')
        self._test(b(r'"foo \"bar\""'), 'foo "bar"')
        self._test(b(r'"foo\\bar"'), r'foo\bar')

    def test_square_brackets(self):
        self._test(b('foo[bar rrr]'), 'foo[bar rrr]')
        self._test(b('"foo[bar rrr]"'), 'foo[bar rrr]')
        self._test(b('[foo bar]def'), '[foo bar]def')
        self._test(b('(foo [bar rrr])'), ('foo', '[bar rrr]'))
        self._test(b('(foo foo[bar rrr])'), ('foo', 'foo[bar rrr]'))

    def test_incomplete_tuple(self):
        self._test_parse_error(b('abc (1 2'), 'Tuple incomplete before "\(1 2"')

    def test_bad_literal(self):
        self._test_parse_error([(b('{99}'), b('abc'))],
                               'Expecting literal of size 99, got 3')

    def test_bad_quoting(self):
        self._test_parse_error(b('"abc next'), """No closing '"'""")

    def _test(self, to_parse, expected, wrap=True):
        if wrap:
            # convenience - expected value should be wrapped in another tuple
            expected = (expected,)
        if not isinstance(to_parse, list):
            to_parse = [to_parse]
        output = parse_response(to_parse)
        self.assertSequenceEqual(output, expected)

    def _test_parse_error(self, to_parse, expected_msg):
        if not isinstance(to_parse, list):
            to_parse = [to_parse]
        self.assertRaisesRegexp(ParseError, expected_msg,
                                parse_response, to_parse)


class TestParseFetchResponse(unittest.TestCase):

    def test_basic(self):
        self.assertEqual(parse_fetch_response(b('4 ()')), {4: {'SEQ': 4}})


    def test_none_special_case(self):
        self.assertEqual(parse_fetch_response([None]), {})


    def test_bad_msgid(self):
        self.assertRaises(ParseError, parse_fetch_response, [b('abc ()')])


    def test_bad_data(self):
        self.assertRaises(ParseError, parse_fetch_response, [b('2 WHAT')])


    def test_missing_data(self):
        self.assertRaises(ParseError, parse_fetch_response, [b('2')])


    def test_simple_pairs(self):
        self.assertEqual(parse_fetch_response([b('23 (ABC 123 StUfF "hello")')]),
                          {23: {'ABC': 123,
                                'STUFF': 'hello',
                                'SEQ': 23}})


    def test_odd_pairs(self):
        self.assertRaises(ParseError, parse_fetch_response, [b('(ONE)')])
        self.assertRaises(ParseError, parse_fetch_response, [b('(ONE TWO THREE)')])


    def test_UID(self):
        self.assertEqual(parse_fetch_response([b('23 (UID 76)')]),
                         {76: {'SEQ': 23}})
        self.assertEqual(parse_fetch_response([b('23 (uiD 76)')]),
                         {76: {'SEQ': 23}})


    def test_not_uid_is_key(self):
        self.assertEqual(parse_fetch_response([b('23 (UID 76)')], uid_is_key=False),
                          {23: {'UID': 76,
                                'SEQ': 23}})


    def test_bad_UID(self):
        self.assertRaises(ParseError, parse_fetch_response, [b('(UID X)')])
        

    def test_FLAGS(self):
        self.assertEqual(parse_fetch_response([b('23 (FLAGS (\Seen Stuff))')]),
                          {23: {'SEQ': 23, 'FLAGS': (r'\Seen', 'Stuff')}})


    def test_multiple_messages(self):
        self.assertEqual(parse_fetch_response(
                                    [b("2 (FLAGS (Foo Bar)) "),
                                     b("7 (FLAGS (Baz Sneeve))")]),
                         {
                            2: {'FLAGS': ('Foo', 'Bar'), 'SEQ': 2},
                            7: {'FLAGS': ('Baz', 'Sneeve'), 'SEQ': 7},
                         })


    def test_literals(self):
        self.assertEqual(parse_fetch_response([(b('1 (RFC822.TEXT {4}'), b('body')),
                                               (b(' RFC822 {21}'), b('Subject: test\r\n\r\nbody')),
                                               b(')')]),
                          {1: {'RFC822.TEXT': 'body',
                               'RFC822': 'Subject: test\r\n\r\nbody',
                               'SEQ': 1}})


    def test_literals_and_keys_with_square_brackets(self):
        self.assertEqual(parse_fetch_response([(b('1 (BODY[TEXT] {11}'), b('Hi there.\r\n')), b(')')]),
                          { 1: {'BODY[TEXT]': 'Hi there.\r\n',
                                'SEQ': 1}})


    def test_BODY_HEADER_FIELDS(self):
        header_text = 'Subject: A subject\r\nFrom: Some one <someone@mail.com>\r\n\r\n'
        self.assertEqual(parse_fetch_response(
            [(b('123 (UID 31710 BODY[HEADER.FIELDS (from subject)] {57}'), b(header_text)), b(')')]),
            { 31710: {'BODY[HEADER.FIELDS (FROM SUBJECT)]': header_text,
                      'SEQ': 123}})

    def test_BODY(self):
         self.check_BODYish_single_part('BODY')
         self.check_BODYish_multipart('BODY')

    def test_BODYSTRUCTURE(self):
         self.check_BODYish_single_part('BODYSTRUCTURE')
         self.check_BODYish_multipart('BODYSTRUCTURE')
    
    def check_BODYish_single_part(self, respType):
        text =  b('123 (UID 317 %s ("TEXT" "PLAIN" ("CHARSET" "us-ascii") NIL NIL "7BIT" 16 1))' % respType)
        parsed = parse_fetch_response([text])
        self.assertEqual(parsed, {317: {respType: ('TEXT', 'PLAIN', ('CHARSET', 'us-ascii'), None, None, '7BIT', 16, 1),
                                         'SEQ': 123 }
                                         })
        self.assertFalse(parsed[317][respType].is_multipart)

    def check_BODYish_multipart(self, respType):
        text = b('123 (UID 269 %s (("TEXT" "HTML" ("CHARSET" "us-ascii") NIL NIL "QUOTED-PRINTABLE" 55 3)' \
                                 '("TEXT" "PLAIN" ("CHARSET" "us-ascii") NIL NIL "7BIT" 26 1) "MIXED"))' \
                                % respType)
        parsed = parse_fetch_response([text])
        self.assertEqual(parsed, {269: {respType: ([('TEXT', 'HTML', ('CHARSET', 'us-ascii'), None, None, 'QUOTED-PRINTABLE', 55, 3),
                                                     ('TEXT', 'PLAIN', ('CHARSET', 'us-ascii'), None, None, '7BIT', 26, 1)],
                                                     'MIXED'),
                                        'SEQ': 123}
                                        })
        self.assertTrue(parsed[269][respType].is_multipart)

    def test_partial_fetch(self):
        body = '01234567890123456789'
        self.assertEqual(parse_fetch_response(
            [(b('123 (UID 367 BODY[]<0> {20}'), b(body)), b(')')]),
            { 367: {'BODY[]<0>': body,
                    'SEQ': 123}})
                    

    def test_INTERNALDATE_normalised(self):
        def check(date_str, expected_dt):
            output = parse_fetch_response([b('3 (INTERNALDATE "%s")' % date_str)])
            actual_dt = output[3]['INTERNALDATE']
            self.assert_(actual_dt.tzinfo is None)   # Returned date should be in local timezone
            expected_dt = datetime_to_native(expected_dt)
            self.assertEqual(actual_dt, expected_dt)

        check(' 9-Feb-2007 17:08:08 -0430',
              datetime(2007, 2, 9, 17, 8, 8, 0, FixedOffset(-4*60 - 30)))
 
        check('12-Feb-2007 17:08:08 +0200',
              datetime(2007, 2, 12, 17, 8, 8, 0, FixedOffset(2*60)))
 
        check(' 9-Dec-2007 17:08:08 +0000',
              datetime(2007, 12, 9, 17, 8, 8, 0, FixedOffset(0)))

    def test_INTERNALDATE(self):
        def check(date_str, expected_dt):
            output = parse_fetch_response([b('3 (INTERNALDATE "%s")' % date_str)], normalise_times=False)
            actual_dt = output[3]['INTERNALDATE']
            self.assertEqual(actual_dt, expected_dt)

        check(' 9-Feb-2007 17:08:08 -0430',
              datetime(2007, 2, 9, 17, 8, 8, 0, FixedOffset(-4*60 - 30)))
 
        check('12-Feb-2007 17:08:08 +0200',
              datetime(2007, 2, 12, 17, 8, 8, 0, FixedOffset(2*60)))
 
        check(' 9-Dec-2007 17:08:08 +0000',
              datetime(2007, 12, 9, 17, 8, 8, 0, FixedOffset(0)))

    def test_mixed_types(self):
        self.assertEqual(parse_fetch_response([(b('1 (INTERNALDATE " 9-Feb-2007 17:08:08 +0100" RFC822 {21}'),
                                                b('Subject: test\r\n\r\nbody')),
                                               b(')')]),
                          {1: {'INTERNALDATE': datetime_to_native(datetime(2007, 2, 9,
                                                                           17, 8, 8, 0,
                                                                           FixedOffset(60))),
                               'RFC822': 'Subject: test\r\n\r\nbody',
                               'SEQ': 1}})


def add_crlf(text):
    return CRLF.join(text.splitlines()) + CRLF


system_offset = FixedOffset.for_system()
def datetime_to_native(dt):
    return dt.astimezone(system_offset).replace(tzinfo=None)


