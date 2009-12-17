# Copyright (c) 2009, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

'''
Unit tests for the FetchTokeniser and FetchParser classes
'''

import unittest
import datetime
from imapclient.imapclient import FetchParser, FetchTokeniser, Literal
from imapclient.fixed_offset import FixedOffset
from pprint import pformat

#TODO: test invalid dates and times
#TODO: more response types  

system_offset = FixedOffset.for_system()
def datetime_to_native(dt):
    return dt.astimezone(system_offset).replace(tzinfo=None)

class TestFetchTokeniser(unittest.TestCase):
    def setUp(self):
        self.t = FetchTokeniser()

    def testEmptyList(self):
        self._test_list('', [])

    def testOneItemList(self):
        self._test_list('123', [123])

    def testWordsInList(self):
        self._test_list('test stuff', ['test', 'stuff'])

    def testQuotedStringInList(self):
        self._test_list('"test stuff" and more', ['test stuff', 'and', 'more'])

    def testNILInList(self):
        self._test_list('test NIL stuff', ['test', None, 'stuff'])

    def testEmptyListPair(self):
        self._test_pairs('FOO ()', [('FOO', [])])

    def testIntPair(self):
        self._test_pairs('FOO 123', [('FOO', 123)])

    def testQuotedStringPair(self):
        self._test_pairs('FOO "abc def"', [('FOO', "abc def")])

    def testComplexListPair(self):
        self._test_pairs('FOO (123 "a b c" \\XYZ)', [('FOO', [123, "a b c", '\\XYZ'])])

    def testMultiplePairs(self):
        self._test_pairs('FOO 123 bar (def "XYZ") MORE "stuff"', [
            ('FOO', 123),
            ('bar', ['def', 'XYZ']),
            ('MORE', 'stuff'),
            ])

    def testNoPairs(self):
        self._test_pairs('', [])

    def testGarbage(self):
        self.assertRaises(ValueError,
                self.t.process_pairs, 'FOO 123 BAH "abc" WHAT?')
        self.assertRaises(ValueError,
                self.t.process_pairs, 'HMMM FOO 123 BAH "abc"')
        self.assertRaises(ValueError,
                self.t.process_pairs, 'FOO 123 BAD BAH "abc"')

    def testLiteral(self):
        self._test_pairs('FOO {21}', [('FOO', Literal(21))])

    def _test_pairs(self, input_, expected):
        output = self.t.process_pairs(input_)
        self.assert_(
                output == expected,
                format_error(input_, output, expected),
            )
        return output

    def _test_list(self, input_, expected):
        output = self.t.process_list(input_)
        self.assert_(
                output == expected,
                format_error(input_, output, expected),
            )
        return output

class TestFetchParser(unittest.TestCase):

    def setUp(self):
        self.p = FetchParser()

    def testCharacterCase(self):
        '''Test handling of varied case in the response type name
        '''
        self._parse_test(
            [r'2 (flaGS (\Deleted Foo \Seen))'],
            {2: {'FLAGS': [r'\Deleted', 'Foo', r'\Seen']}}
            )

    def testGarbage(self):
        self.assertRaises(ValueError, self.p, [r'2 (FLAGS (\Deleted) MORE)'])


    def test_INTERNALDATE(self):

        def check(date_str, expected_dt):
            output = self.p(['3 (INTERNALDATE "%s")' % date_str])
            assert output.keys() == [3]
            assert output[3].keys() == ['INTERNALDATE']
            actual_dt = output[3]['INTERNALDATE']

            # Returned date should be in local timezone
            self.assert_(actual_dt.tzinfo is None)

            expected_dt = datetime_to_native(expected_dt)
            self.assert_(actual_dt == expected_dt,
                         '%s != %s' % (actual_dt, expected_dt))

        dt = check(' 9-Feb-2007 17:08:08 -0430',
                   datetime.datetime(2007, 2, 9, 17, 8, 8, 0, FixedOffset(-4*60 - 30)))
 
        dt = check('12-Feb-2007 17:08:08 +0200',
                   datetime.datetime(2007, 2, 12, 17, 8, 8, 0, FixedOffset(2*60)))
 
        dt = check(' 9-Dec-2007 17:08:08 +0000',
                   datetime.datetime(2007, 12, 9, 17, 8, 8, 0, FixedOffset(0)))


    def testMultipleTypes(self):
        '''Test multiple response types'''
        self._parse_test(
            [r'2 (FLAGS (\Deleted Foo \Seen) INTERNALDATE " 9-Feb-2007 17:08:08 +0000")'],
            {2: {
                    'FLAGS': [r'\Deleted', 'Foo', r'\Seen'],
                    'INTERNALDATE': datetime_to_native(datetime.datetime(2007, 2, 9,
                                                                         17, 8, 8, 0,
                                                                         FixedOffset(0)))
                    }
                }
            )

    def testMultipleMessages(self):
        '''Test with multple messages in the response
        '''
        self._parse_test(
            [
                r'2 (FLAGS (Foo Bar))',
                r'7 (FLAGS (Baz Sneeve))',
                ],
            {
                2: {'FLAGS': ['Foo', 'Bar']},
                7: {'FLAGS': ['Baz', 'Sneeve']},
                }
            )

    def testLiteral(self):
        '''Test literal handling
        '''
        self._parse_test(
            [('1 (RFC822 {21}', 'Subject: test\r\n\r\nbody'), ')'],
            { 1: {'RFC822': 'Subject: test\r\n\r\nbody'} }
            )

    def testMultipleLiterals(self):
        self._parse_test(
            [
                ('1 (RFC822.TEXT {4}', 'body'),
                (' RFC822 {21}', 'Subject: test\r\n\r\nbody'),
                ')'
                ],
            { 1: {
                    'RFC822.TEXT': 'body',
                    'RFC822': 'Subject: test\r\n\r\nbody',
                    }
                }
            )

    def testMultiTypesWithLiteral(self):
        self._parse_test(
            [
                ('1 (INTERNALDATE " 9-Feb-2007 17:08:08 +0100" RFC822 {21}',
                      'Subject: test\r\n\r\nbody'),
                ')'
                ],
            {1: {
                    'INTERNALDATE': datetime_to_native(datetime.datetime(2007, 2, 9,
                                                                         17, 8, 8, 0,
                                                                         FixedOffset(60))),
                    'RFC822': 'Subject: test\r\n\r\nbody',
                    }
                }
            )

    def testLiteralsWithSections(self):
        self._parse_test(
            [('1 (BODY[TEXT] {11}', 'Hi there.\r\n'), ')'],
            { 1: {'BODY[TEXT]': 'Hi there.\r\n',} }
            )

    def testLiteralsWithSectionsAndOtherParts(self):
        self._parse_test(
            [('1 (FLAGS (\\Seen) UID 2 BODY[HEADER.FIELDS (FROM)] {21}',
              'From: foo@foo.com\r\n'), ')'],
            {2: { 'BODY[HEADER.FIELDS (FROM)]': 'From: foo@foo.com\r\n',
                  'FLAGS': ['\\Seen'],
                   }
                }
            )

    def testUID(self):
        '''Test UID handling. The UID is returned instead of the given message
        ID if present.
        '''
        self._parse_test(
            ['1 (UID 8)'],
            {8: {}}
            )

    def _parse_test(self, to_parse, expected):
        output = self.p(to_parse)
        self.assert_(
                output == expected,
                format_error(to_parse, output, expected),
            )

def format_error(input_, output, expected):
    return 'failed for:\n%s\ngot:\n%s\nexpected:\n%s' % (
                pformat(input_),
                pformat(output),
                pformat(expected),
            )

if __name__ == '__main__':
    unittest.main()
