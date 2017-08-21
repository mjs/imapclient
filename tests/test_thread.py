# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from .imapclient_test import IMAPClientTest
from .util import Mock


class TestThread(IMAPClientTest):

    def setUp(self):
        super(TestThread, self).setUp()
        self.client._cached_capabilities = (b'THREAD=REFERENCES',)
        self.client._raw_command_untagged = Mock()
        self.client._raw_command_untagged.return_value = [b'(1 2)(3)(4 5 6)']

    def check_call(self, expected_args):
        self.client._raw_command_untagged.assert_called_once_with(
            b'THREAD', expected_args)

    def test_no_thread_support(self):
        self.client._cached_capabilities = (b'NOT-THREAD',)
        self.assertRaises(ValueError, self.client.thread)

    def test_unsupported_algorithm(self):
        self.client._cached_capabilities = (b'THREAD=FOO',)
        self.assertRaises(ValueError, self.client.thread)

    def test_defaults(self):
        threads = self.client.thread()

        self.check_call([b'REFERENCES', b'UTF-8', b'ALL'])
        self.assertSequenceEqual(threads, ((1, 2), (3,), (4, 5, 6)))

    def test_all_args(self):
        self.client._cached_capabilities = (b'THREAD=COTTON',)

        self.client.thread('COTTON', ['TEXT', '\u261e'], 'UTF-7')

        self.check_call([b'COTTON', b'UTF-7', b'TEXT', b'+Jh4-'])
