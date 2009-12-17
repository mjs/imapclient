# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

# Copyright 2009 Menno Smits

'''
Unit tests for the FetchTokeniser and FetchParser classes
'''

from textwrap import dedent
import unittest
from imapclient.response_parser import parse_response, parse_fetch_response, ParseError
from imapclient.fixed_offset import FixedOffset
from pprint import pformat

#TODO: tokenising tests
#TODO: test invalid dates and times
#TODO: more response types
#TODO: clean up this file


CRLF = '\r\n'

class TestParseResponse(unittest.TestCase):

    def test_unquoted(self):
        self._test('FOO', 'FOO')
        self._test('F.O:-O_0;', 'F.O:-O_0;')
        self._test(r'\Seen', r'\Seen')

    def test_string(self):
        self._test('"TEST"', 'TEST')

    def test_int(self):
        self._test('45', 45)

    def test_nil(self):
        self._test('NIL', None)

    def test_empty_tuple(self):
        self._test('()', ())

    def test_tuple(self):
        self._test('(123 "foo" GeE)', (123, 'foo', 'GeE'))

    def test_int_and_tuple(self):
        self._test('1 (123 "foo")', (1, (123, 'foo')), wrap=False)

    def test_nested_tuple(self):
        self._test('(123 "foo" ("more" NIL) 66)',
                   (123, "foo", ("more", None), 66))

    def test_deeper_nest_tuple(self):
        self._test('(123 "foo" ((0 1 2) "more" NIL) 66)',
                   (123, "foo", ((0, 1, 2), "more", None), 66))

    def test_complex_mixed(self):
        self._test('((FOO "PLAIN" ("CHARSET" "US-ASCII") NIL NIL "7BIT" 1152 23)'
                   '("TEXT" "PLAIN" ("CHARSET" "US-ASCII" "NAME" "cc.diff") '
                   '"<hi.there>" "foo" "BASE64" 4554 73) "MIXED")',
                   (('FOO', 'PLAIN', ('CHARSET', 'US-ASCII'), None, None, '7BIT', 1152, 23),
                    ('TEXT', 'PLAIN', ('CHARSET', 'US-ASCII', 'NAME', 'cc.diff'),
                    '<hi.there>', 'foo', 'BASE64', 4554, 73), 'MIXED'))


    def test_literal(self):
        literal_text = add_crlf(dedent("""\
            012
            abc def XYZ
            """))
        self._test('{18}' + CRLF + literal_text, literal_text)


    def test_literal_with_more(self):
        literal_text = add_crlf(dedent("""\
            012
            abc def XYZ
            """))
        response = add_crlf(dedent("""\
            (12 "foo" {18}
            %s)
            """) % literal_text)
        self._test(response, (12, 'foo', literal_text))


    def test_incomplete_tuple(self):
        self._test_parse_error('abc (1 2', 'Tuple incomplete before "(1 2"')


    def test_bad_literal(self):
        self._test_parse_error('{99} abc', 'No CRLF after {99}')


    def test_bad_quoting(self):
        self._test_parse_error('"abc next', 'No closing quotation: "abc next')


    def _test(self, to_parse, expected, wrap=True):
        if wrap:
            # convenience - expected value should be wrapped in another tuple
            expected = (expected,)
        output = parse_response(to_parse)
        self.assert_(
                output == expected,
                format_error(to_parse, output, expected),
            )

    def _test_parse_error(self, to_parse, expected_msg):
        try:
            parse_response(to_parse)
            self.fail("didn't raise an exception")
        except ParseError, err:
            self.assert_(expected_msg == str(err),
                         'got ParseError with wrong msg: %r' % str(err))


system_offset = FixedOffset.for_system()
def datetime_to_native(dt):
    return dt.astimezone(system_offset).replace(tzinfo=None)


class TestParseFetchResponse(unittest.TestCase):

    def test_basic(self):
        self.assertEquals(parse_fetch_response('* 4 FETCH ()'), {4: {}})
        self.assertEquals(parse_fetch_response('* 4 fEtCh ()'), {4: {}})


    def test_non_fetch(self):
        self.assertRaises(ParseError, parse_fetch_response, '* 4 OTHER ()')


    def test_bad_msgid(self):
        self.assertRaises(ParseError, parse_fetch_response, '* abc FETCH ()')


    def test_bad_data(self):
        self.assertRaises(ParseError, parse_fetch_response, '* 2 FETCH WHAT')


    def test_simple_pairs(self):
        self.assertEquals(parse_fetch_response('* 23 FETCH (ABC 123 StUfF "hello")'),
                          {23: {'ABC': 123,
                                'STUFF': 'hello'}})


    def test_odd_pairs(self):
        self.assertRaises(ParseError, parse_fetch_response, '* 2 FETCH (ONE)')
        self.assertRaises(ParseError, parse_fetch_response, '* 2 FETCH (ONE TWO THREE)')


    def test_UID(self):
        self.assertEquals(parse_fetch_response('* 23 FETCH (UID 76)'),
                          {76: {}})
        self.assertEquals(parse_fetch_response('* 23 FETCH (uiD 76)'),
                          {76: {}})


    def test_bad_UID(self):
        self.assertRaises(ParseError, parse_fetch_response, '* 2 FETCH (UID X)')
        

    def test_FLAGS(self):
        self.assertEquals(parse_fetch_response('* 23 FETCH (FLAGS (\Seen Stuff))'),
                          {23: {'FLAGS': (r'\Seen', 'Stuff')}})


    def test_multiple_messages(self):
        self.fail()


    def test_INTERNALDATE(self):
        self.fail()

#         def check(date_str, expected_dt):
#             output = self.p(['3 (INTERNALDATE "%s")' % date_str])
#             assert output.keys() == [3]
#             assert output[3].keys() == ['INTERNALDATE']
#             actual_dt = output[3]['INTERNALDATE']

#             # Returned date should be in local timezone
#             self.assert_(actual_dt.tzinfo is None)

#             expected_dt = datetime_to_native(expected_dt)
#             self.assert_(actual_dt == expected_dt,
#                          '%s != %s' % (actual_dt, expected_dt))

#         dt = check(' 9-Feb-2007 17:08:08 -0430',
#                    datetime.datetime(2007, 2, 9, 17, 8, 8, 0, FixedOffset(-4*60 - 30)))
 
#         dt = check('12-Feb-2007 17:08:08 +0200',
#                    datetime.datetime(2007, 2, 12, 17, 8, 8, 0, FixedOffset(2*60)))
 
#         dt = check(' 9-Dec-2007 17:08:08 +0000',
#                    datetime.datetime(2007, 12, 9, 17, 8, 8, 0, FixedOffset(0)))


#     def testMultipleMessages(self):
#         '''Test with multple messages in the response
#         '''
#         self._parse_test(
#             [
#                 r'2 (FLAGS (Foo Bar))',
#                 r'7 (FLAGS (Baz Sneeve))',
#                 ],
#             {
#                 2: {'FLAGS': ['Foo', 'Bar']},
#                 7: {'FLAGS': ['Baz', 'Sneeve']},
#                 }
#             )

#     def testLiteral(self):
#         '''Test literal handling
#         '''
#         self._parse_test(
#             [('1 (RFC822 {21}', 'Subject: test\r\n\r\nbody'), ')'],
#             { 1: {'RFC822': 'Subject: test\r\n\r\nbody'} }
#             )

#     def testMultipleLiterals(self):
#         self._parse_test(
#             [
#                 ('1 (RFC822.TEXT {4}', 'body'),
#                 (' RFC822 {21}', 'Subject: test\r\n\r\nbody'),
#                 ')'
#                 ],
#             { 1: {
#                     'RFC822.TEXT': 'body',
#                     'RFC822': 'Subject: test\r\n\r\nbody',
#                     }
#                 }
#             )

#     def testMultiTypesWithLiteral(self):
#         self._parse_test(
#             [
#                 ('1 (INTERNALDATE " 9-Feb-2007 17:08:08 +0100" RFC822 {21}',
#                       'Subject: test\r\n\r\nbody'),
#                 ')'
#                 ],
#             {1: {
#                     'INTERNALDATE': datetime_to_native(datetime.datetime(2007, 2, 9,
#                                                                          17, 8, 8, 0,
#                                                                          FixedOffset(60))),
#                     'RFC822': 'Subject: test\r\n\r\nbody',
#                     }
#                 }
#             )

#     def testLiteralsWithSections(self):
#         self._parse_test(
#             [('1 (BODY[TEXT] {11}', 'Hi there.\r\n'), ')'],
#             { 1: {'BODY[TEXT]': 'Hi there.\r\n',} }
#             )

#     def testLiteralsWithSectionsAndOtherParts(self):
#         self._parse_test(
#             [('1 (FLAGS (\\Seen) UID 2 BODY[HEADER.FIELDS (FROM)] {21}',
#               'From: foo@foo.com\r\n'), ')'],
#             {2: { 'BODY[HEADER.FIELDS (FROM)]': 'From: foo@foo.com\r\n',
#                   'FLAGS': ['\\Seen'],
#                    }
#                 }
#             )



def format_error(input_, output, expected):
    return 'failed for:\n%s\ngot:\n%s\nexpected:\n%s' % (
                pformat(input_),
                pformat(output),
                pformat(expected),
            )


def add_crlf(text):
    return CRLF.join(text.splitlines()) + CRLF


if __name__ == '__main__':
    unittest.main()
