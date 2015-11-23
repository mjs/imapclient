# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

'''
Unit tests for the FetchTokeniser and FetchParser classes
'''

from __future__ import unicode_literals

from datetime import datetime

from imapclient.datetime_util import datetime_to_native
from imapclient.fixed_offset import FixedOffset
from imapclient.response_parser import (
    parse_response,
    parse_message_list,
    parse_fetch_response,
    ParseError,
)
from imapclient.response_types import Envelope, Address
from imapclient.test.util import unittest

# TODO: test invalid dates and times


CRLF = b'\r\n'


class TestParseResponse(unittest.TestCase):

    def test_unquoted(self):
        self._test(b'FOO', b'FOO')
        self._test(b'F.O:-O_0;', b'F.O:-O_0;')
        self._test(br'\Seen', br'\Seen')

    def test_string(self):
        self._test(b'"TEST"', b'TEST')

    def test_int(self):
        self._test(b'45', 45)

    def test_nil(self):
        self._test(b'NIL', None)

    def test_empty_tuple(self):
        self._test(b'()', ())

    def test_tuple(self):
        self._test(b'(123 "foo" GeE)', (123, b'foo', b'GeE'))

    def test_int_and_tuple(self):
        self._test(b'1 (123 "foo")', (1, (123, b'foo')), wrap=False)

    def test_nested_tuple(self):
        self._test(b'(123 "foo" ("more" NIL) 66)',
                   (123, b"foo", (b"more", None), 66))

    def test_deeper_nest_tuple(self):
        self._test(b'(123 "foo" ((0 1 2) "more" NIL) 66)',
                   (123, b"foo", ((0, 1, 2), b"more", None), 66))

    def test_complex_mixed(self):
        self._test(b'((FOO "PLAIN" ("CHARSET" "US-ASCII") NIL NIL "7BIT" 1152 23) '
                   b'("TEXT" "PLAIN" ("CHARSET" "US-ASCII" "NAME" "cc.diff") '
                   b'"<hi.there>" "foo" "BASE64" 4554 73) "MIXED")',
                   ((b'FOO', b'PLAIN', (b'CHARSET', b'US-ASCII'), None, None, b'7BIT', 1152, 23),
                    (b'TEXT', b'PLAIN', (b'CHARSET', b'US-ASCII', b'NAME', b'cc.diff'),
                     b'<hi.there>', b'foo', b'BASE64', 4554, 73), b'MIXED'))

    def test_envelopey(self):
        self._test(b'(UID 5 ENVELOPE ("internal_date" "subject" '
                   b'(("name" NIL "address1" "domain1.com")) '
                   b'((NIL NIL "address2" "domain2.com")) '
                   b'(("name" NIL "address3" "domain3.com")) '
                   b'((NIL NIL "address4" "domain4.com")) '
                   b'NIL NIL "<reply-to-id>" "<msg_id>"))',
                   (b'UID',
                    5,
                    b'ENVELOPE',
                    (b'internal_date',
                     b'subject',
                     ((b'name', None, b'address1', b'domain1.com'),),
                     ((None, None, b'address2', b'domain2.com'),),
                     ((b'name', None, b'address3', b'domain3.com'),),
                     ((None, None, b'address4', b'domain4.com'),),
                     None,
                     None,
                     b'<reply-to-id>',
                     b'<msg_id>')))

    def test_envelopey_quoted(self):
        self._test(b'(UID 5 ENVELOPE ("internal_date" "subject with \\"quotes\\"" '
                   b'(("name" NIL "address1" "domain1.com")) '
                   b'((NIL NIL "address2" "domain2.com")) '
                   b'(("name" NIL "address3" "domain3.com")) '
                   b'((NIL NIL "address4" "domain4.com")) '
                   b'NIL NIL "<reply-to-id>" "<msg_id>"))',
                   (b'UID',
                    5,
                    b'ENVELOPE',
                    (b'internal_date',
                     b'subject with "quotes"',
                     ((b'name', None, b'address1', b'domain1.com'),),
                     ((None, None, b'address2', b'domain2.com'),),
                     ((b'name', None, b'address3', b'domain3.com'),),
                     ((None, None, b'address4', b'domain4.com'),),
                     None,
                     None,
                     b'<reply-to-id>',
                     b'<msg_id>')))

    def test_literal(self):
        literal_text = add_crlf(
            b"012\n"
            b"abc def XYZ\n"
        )
        self._test([(b'{18}', literal_text)], literal_text)

    def test_literal_with_more(self):
        literal_text = add_crlf(
            b"012\n"
            b"abc def XYZ\n"
        )
        response = [(b'(12 "foo" {18}', literal_text), b")"]
        self._test(response, (12, b'foo', literal_text))

    def test_quoted_specials(self):
        self._test(br'"\"foo bar\""', b'"foo bar"')
        self._test(br'"foo \"bar\""', b'foo "bar"')
        self._test(br'"foo\\bar"', br'foo\bar')

    def test_square_brackets(self):
        self._test(b'foo[bar rrr]', b'foo[bar rrr]')
        self._test(b'"foo[bar rrr]"', b'foo[bar rrr]')
        self._test(b'[foo bar]def', b'[foo bar]def')
        self._test(b'(foo [bar rrr])', (b'foo', b'[bar rrr]'))
        self._test(b'(foo foo[bar rrr])', (b'foo', b'foo[bar rrr]'))

    def test_incomplete_tuple(self):
        self._test_parse_error(b'abc (1 2', 'Tuple incomplete before "\(1 2"')

    def test_bad_literal(self):
        self._test_parse_error([(b'{99}', b'abc')],
                               'Expecting literal of size 99, got 3')

    def test_bad_quoting(self):
        self._test_parse_error(b'"abc next', """No closing '"'""")

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
        self.assertRaisesRegex(ParseError, expected_msg,
                               parse_response, to_parse)


class TestParseMessageList(unittest.TestCase):

    def test_basic(self):
        out = parse_message_list([b'1 2 3'])
        self.assertSequenceEqual(out, [1, 2, 3])
        self.assertEqual(out.modseq, None)

    def test_one_id(self):
        self.assertSequenceEqual(parse_message_list([b'4']), [4])

    def test_modseq(self):
        out = parse_message_list([b'1 2 3 (modseq 999)'])
        self.assertSequenceEqual(out, [1, 2, 3])
        self.assertEqual(out.modseq, 999)

    def test_modseq_no_space(self):
        out = parse_message_list([b'1 2 3(modseq 999)'])
        self.assertSequenceEqual(out, [1, 2, 3])
        self.assertEqual(out.modseq, 999)

    def test_modseq_interleaved(self):
        # Unlikely but test it anyway.
        out = parse_message_list([b'1 2 (modseq 9) 3 4'])
        self.assertSequenceEqual(out, [1, 2, 3, 4])
        self.assertEqual(out.modseq, 9)


class TestParseFetchResponse(unittest.TestCase):

    def test_basic(self):
        self.assertEqual(parse_fetch_response([b'4 ()']), {4: {b'SEQ': 4}})

    def test_none_special_case(self):
        self.assertEqual(parse_fetch_response([None]), {})

    def test_bad_msgid(self):
        self.assertRaises(ParseError, parse_fetch_response, [b'abc ()'])

    def test_bad_data(self):
        self.assertRaises(ParseError, parse_fetch_response, [b'2 WHAT'])

    def test_missing_data(self):
        self.assertRaises(ParseError, parse_fetch_response, [b'2'])

    def test_simple_pairs(self):
        self.assertEqual(parse_fetch_response([b'23 (ABC 123 StUfF "hello")']),
                         {23: {b'ABC': 123,
                               b'STUFF': b'hello',
                               b'SEQ': 23}})

    def test_odd_pairs(self):
        self.assertRaises(ParseError, parse_fetch_response, [b'(ONE)'])
        self.assertRaises(ParseError, parse_fetch_response, [b'(ONE TWO THREE)'])

    def test_UID(self):
        self.assertEqual(parse_fetch_response([b'23 (UID 76)']),
                         {76: {b'SEQ': 23}})
        self.assertEqual(parse_fetch_response([b'23 (uiD 76)']),
                         {76: {b'SEQ': 23}})

    def test_not_uid_is_key(self):
        self.assertEqual(parse_fetch_response([b'23 (UID 76)'], uid_is_key=False),
                         {23: {b'UID': 76,
                               b'SEQ': 23}})

    def test_bad_UID(self):
        self.assertRaises(ParseError, parse_fetch_response, [b'(UID X)'])

    def test_FLAGS(self):
        self.assertEqual(parse_fetch_response([b'23 (FLAGS (\Seen Stuff))']),
                         {23: {b'SEQ': 23, b'FLAGS': (br'\Seen', b'Stuff')}})

    def test_multiple_messages(self):
        self.assertEqual(parse_fetch_response(
            [b"2 (FLAGS (Foo Bar)) ",
             b"7 (FLAGS (Baz Sneeve))"]),
            {
            2: {b'FLAGS': (b'Foo', b'Bar'), b'SEQ': 2},
            7: {b'FLAGS': (b'Baz', b'Sneeve'), b'SEQ': 7},
        })

    def test_same_message_appearing_multiple_times(self):
        # This can occur when server sends unsolicited FETCH responses
        # (e.g. RFC 4551)
        self.assertEqual(parse_fetch_response(
            [b"2 (FLAGS (Foo Bar)) ",
             b"2 (MODSEQ 4)"]),
            {2: {b'FLAGS': (b'Foo', b'Bar'), b'SEQ': 2, b'MODSEQ': 4}})

    def test_literals(self):
        self.assertEqual(parse_fetch_response([(b'1 (RFC822.TEXT {4}', b'body'),
                                               (b' RFC822 {21}', b'Subject: test\r\n\r\nbody'),
                                               b')']),
                         {1: {b'RFC822.TEXT': b'body',
                              b'RFC822': b'Subject: test\r\n\r\nbody',
                              b'SEQ': 1}})

    def test_literals_and_keys_with_square_brackets(self):
        self.assertEqual(parse_fetch_response([(b'1 (BODY[TEXT] {11}', b'Hi there.\r\n'), b')']),
                         {1: {b'BODY[TEXT]': b'Hi there.\r\n',
                              b'SEQ': 1}})

    def test_BODY_HEADER_FIELDS(self):
        header_text = b'Subject: A subject\r\nFrom: Some one <someone@mail.com>\r\n\r\n'
        self.assertEqual(parse_fetch_response(
            [(b'123 (UID 31710 BODY[HEADER.FIELDS (from subject)] {57}', header_text), b')']),
            {31710: {b'BODY[HEADER.FIELDS (FROM SUBJECT)]': header_text,
                     b'SEQ': 123}})

    def test_BODY(self):
        self.check_BODYish_single_part(b'BODY')
        self.check_BODYish_multipart(b'BODY')
        self.check_BODYish_nested_multipart(b'BODY')

    def test_BODYSTRUCTURE(self):
        self.check_BODYish_single_part(b'BODYSTRUCTURE')
        self.check_BODYish_nested_multipart(b'BODYSTRUCTURE')

    def check_BODYish_single_part(self, respType):
        text = b'123 (UID 317 ' + respType + \
            b'("TEXT" "PLAIN" ("CHARSET" "us-ascii") NIL NIL "7BIT" 16 1))'
        parsed = parse_fetch_response([text])
        self.assertEqual(parsed, {
            317: {
                respType: (b'TEXT', b'PLAIN', (b'CHARSET', b'us-ascii'), None, None, b'7BIT', 16, 1),
                b'SEQ': 123
            }
        })
        self.assertFalse(parsed[317][respType].is_multipart)

    def check_BODYish_multipart(self, respType):
        text = b'123 (UID 269 ' + respType + b' ' \
               b'(("TEXT" "HTML" ("CHARSET" "us-ascii") NIL NIL "QUOTED-PRINTABLE" 55 3)' \
               b'("TEXT" "PLAIN" ("CHARSET" "us-ascii") NIL NIL "7BIT" 26 1) "MIXED"))'
        parsed = parse_fetch_response([text])
        self.assertEqual(parsed, {
            269: {
                respType: ([(b'TEXT', b'HTML', (b'CHARSET', b'us-ascii'), None, None, b'QUOTED-PRINTABLE', 55, 3),
                            (b'TEXT', b'PLAIN', (b'CHARSET', b'us-ascii'), None, None, b'7BIT', 26, 1)],
                           b'MIXED'),
                b'SEQ': 123}
        })
        self.assertTrue(parsed[269][respType].is_multipart)

    def check_BODYish_nested_multipart(self, respType):
        text = b'1 (' + respType + b'(' \
               b'(' \
            b'("text" "html" ("charset" "utf-8") NIL NIL "7bit" 97 3 NIL NIL NIL NIL)' \
            b'("text" "plain" ("charset" "utf-8") NIL NIL "7bit" 62 3 NIL NIL NIL NIL)' \
            b'"alternative" ("boundary" "===============8211050864078048428==") NIL NIL NIL' \
               b')' \
               b'("text" "plain" ("charset" "utf-8") NIL NIL "7bit" 16 1 NIL ("attachment" ("filename" "attachment.txt")) NIL NIL) ' \
               b'"mixed" ("boundary" "===============0373402508605428821==") NIL NIL NIL))'

        parsed = parse_fetch_response([text])
        self.assertEqual(parsed, {1: {
            respType: (
                [
                    (
                        [
                            (b'text', b'html', (b'charset', b'utf-8'), None,
                             None, b'7bit', 97, 3, None, None, None, None),
                            (b'text', b'plain', (b'charset', b'utf-8'), None,
                             None, b'7bit', 62, 3, None, None, None, None)
                        ], b'alternative', (b'boundary', b'===============8211050864078048428=='), None, None, None
                    ),
                    (b'text', b'plain', (b'charset', b'utf-8'), None, None, b'7bit', 16, 1,
                     None, (b'attachment', (b'filename', b'attachment.txt')), None, None)
                ], b'mixed', (b'boundary', b'===============0373402508605428821=='), None, None, None,
            ),
            b'SEQ': 1,
        }})
        self.assertTrue(parsed[1][respType].is_multipart)
        self.assertTrue(parsed[1][respType][0][0].is_multipart)
        self.assertFalse(parsed[1][respType][0][0][0][0].is_multipart)

    def test_partial_fetch(self):
        body = b'01234567890123456789'
        self.assertEqual(parse_fetch_response(
            [(b'123 (UID 367 BODY[]<0> {20}', body), b')']),
            {367: {b'BODY[]<0>': body,
                   b'SEQ': 123}})

    def test_ENVELOPE(self):
        envelope_str = (b'1 (ENVELOPE ( '
                        b'"Sun, 24 Mar 2013 22:06:10 +0200" '
                        b'"subject" '
                        b'(("name" NIL "address1" "domain1.com")) '     # from (name and address)
                        b'((NIL NIL "address2" "domain2.com")) '        # sender (just address)
                        b'(("name" NIL "address3" "domain3.com") NIL) '  # reply to
                        b'NIL'                                          # to (no address)
                        b'((NIL NIL "address4" "domain4.com") '         # cc
                        b'("person" NIL "address4b" "domain4b.com")) '
                        b'NIL '                                         # bcc
                        b'"<reply-to-id>" '
                        b'"<msg_id>"))')

        output = parse_fetch_response([envelope_str], normalise_times=False)

        self.assertSequenceEqual(output[1][b'ENVELOPE'],
                                 Envelope(
            datetime(2013, 3, 24, 22, 6, 10, tzinfo=FixedOffset(120)),
            b"subject",
            (Address(b"name", None, b"address1", b"domain1.com"),),
            (Address(None, None, b"address2", b"domain2.com"),),
            (Address(b"name", None, b"address3", b"domain3.com"),),
            None,
            (Address(None, None, b"address4", b"domain4.com"),
             Address(b"person", None, b"address4b", b"domain4b.com")),
            None, b"<reply-to-id>", b"<msg_id>"
        )
        )

    def test_ENVELOPE_with_no_date(self):
        envelope_str = (
            b'1 (ENVELOPE ( '
            b'NIL '
            b'"subject" '
            b'NIL '
            b'NIL '
            b'NIL '
            b'NIL '
            b'NIL '
            b'NIL '
            b'"<reply-to-id>" '
            b'"<msg_id>"))'
        )

        output = parse_fetch_response([envelope_str], normalise_times=False)

        self.assertSequenceEqual(output[1][b'ENVELOPE'],
                                 Envelope(
            None,
            b"subject",
            None,
            None,
            None,
            None,
            None,
            None,
            b"<reply-to-id>", b"<msg_id>"
        )
        )

    def test_ENVELOPE_with_invalid_date(self):
        envelope_str = (b'1 (ENVELOPE ( '
                        b'"wtf" '  # bad date
                        b'"subject" '
                        b'NIL NIL NIL NIL NIL NIL '
                        b'"<reply-to-id>" "<msg_id>"))')

        output = parse_fetch_response([envelope_str], normalise_times=False)

        self.assertSequenceEqual(output[1][b'ENVELOPE'],
                                 Envelope(
            None,
            b"subject",
            None, None, None, None, None, None,
            b"<reply-to-id>", b"<msg_id>",
        )
        )

    def test_ENVELOPE_with_empty_addresses(self):
        envelope_str = (b'1 (ENVELOPE ( '
                        b'NIL '
                        b'"subject" '
                        b'(("name" NIL "address1" "domain1.com") NIL) '
                        b'(NIL (NIL NIL "address2" "domain2.com")) '
                        b'(("name" NIL "address3" "domain3.com") NIL ("name" NIL "address3b" "domain3b.com")) '
                        b'NIL'
                        b'((NIL NIL "address4" "domain4.com") '
                        b'("person" NIL "address4b" "domain4b.com")) '
                        b'NIL "<reply-to-id>" "<msg_id>"))')

        output = parse_fetch_response([envelope_str], normalise_times=False)

        self.assertSequenceEqual(output[1][b'ENVELOPE'],
                                 Envelope(
            None,
            b"subject",
            (Address(b"name", None, b"address1", b"domain1.com"),),
            (Address(None, None, b"address2", b"domain2.com"),),
            (Address(b"name", None, b"address3", b"domain3.com"),
             Address(b"name", None, b"address3b", b"domain3b.com")),
            None,
            (Address(None, None, b"address4", b"domain4.com"),
             Address(b"person", None, b"address4b", b"domain4b.com")),
            None, b"<reply-to-id>", b"<msg_id>"
        )
        )

    def test_INTERNALDATE(self):
        out = parse_fetch_response(
            [b'1 (INTERNALDATE " 9-Feb-2007 17:08:08 -0430")'],
            normalise_times=False
        )
        self.assertEqual(
            out[1][b'INTERNALDATE'],
            datetime(2007, 2, 9, 17, 8, 8, 0, FixedOffset(-4 * 60 - 30))
        )

    def test_INTERNALDATE_normalised(self):
        output = parse_fetch_response([b'3 (INTERNALDATE " 9-Feb-2007 17:08:08 -0430")'])
        dt = output[3][b'INTERNALDATE']
        self.assertTrue(dt.tzinfo is None)   # Returned date should be in local timezone
        expected_dt = datetime_to_native(
            datetime(2007, 2, 9, 17, 8, 8, 0, FixedOffset(-4 * 60 - 30)))
        self.assertEqual(dt, expected_dt)

    def test_mixed_types(self):
        self.assertEqual(parse_fetch_response([(
            b'1 (INTERNALDATE " 9-Feb-2007 17:08:08 +0100" RFC822 {21}',
            b'Subject: test\r\n\r\nbody'
        ), b')']), {
            1: {
                b'INTERNALDATE': datetime_to_native(datetime(2007, 2, 9, 17, 8, 8, 0, FixedOffset(60))),
                b'RFC822': b'Subject: test\r\n\r\nbody',
                b'SEQ': 1
            }
        })

    def test_Address_str(self):
        self.assertEqual(str(Address(b"Mary Jane", None, b"mary", b"jane.org")),
                         "Mary Jane <mary@jane.org>")

        self.assertEqual(str(Address("Mary Jane", None, "mary", "jane.org")),
                         "Mary Jane <mary@jane.org>")



def add_crlf(text):
    return CRLF.join(text.splitlines()) + CRLF
