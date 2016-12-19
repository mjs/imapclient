# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from .imapclient_test import IMAPClientTest
from .util import Mock


class TestSort(IMAPClientTest):

    def setUp(self):
        super(TestSort, self).setUp()
        self.client._cached_capabilities = (b'SORT',)
        self.client._raw_command_untagged = Mock()
        self.client._raw_command_untagged.return_value = b'9 8 7'

    def check_call(self, expected_args):
        self.client._raw_command_untagged.assert_called_once_with(
            b'SORT', expected_args, unpack=True)

    def test_no_support(self):
        self.client._cached_capabilities = (b'BLAH',)
        self.assertRaises(ValueError, self.client.sort, 'ARRIVAL')

    def test_single_criteria(self):
        ids = self.client.sort('arrival')

        self.check_call([b'(ARRIVAL)', b'UTF-8', b'ALL'])
        self.assertSequenceEqual(ids, [9, 8, 7])

    def test_multiple_criteria(self):
        self.client.sort(['arrival', b'SUBJECT'])

        self.check_call([b'(ARRIVAL SUBJECT)', b'UTF-8', b'ALL'])

    def test_all_args(self):
        self.client.sort('arrival', ['TEXT', '\u261e'], 'UTF-7')

        self.check_call([b'(ARRIVAL)', b'UTF-7', b'TEXT', b'+Jh4-'])
