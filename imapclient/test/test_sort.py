# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from six import PY3

from .imapclient_test import IMAPClientTest


sort_command = 'sort' if PY3 else b'sort'


class TestSort(IMAPClientTest):

    def setUp(self):
        super(TestSort, self).setUp()
        self.client._cached_capabilities = (b'SORT',)

    def test_no_support(self):
        self.client._cached_capabilities = (b'BLAH',)
        self.assertRaises(ValueError, self.client.thread)

    def test_without_uid(self):
        self.client.use_uid = False
        self.client._imap.sort.return_value = ('OK', [b'9 8 7'])

        ids = self.client.sort('arrival')

        self.client._imap.sort.assert_called_once_with(
            '(ARRIVAL)',
            b'UTF-8',
            b'(ALL)',
        )
        self.assertSequenceEqual(ids, [9, 8, 7])

    def test_with_uid(self):
        self.client.use_uid = True
        self.client._imap.uid.return_value = ('OK', [b'9 8 7'])

        ids = self.client.sort(['foo', 'bar'])

        self.client._imap.uid.assert_called_once_with(
            sort_command,
            '(FOO BAR)',
            b'UTF-8',
            b'(ALL)',
        )
        self.assertSequenceEqual(ids, [9, 8, 7])

    def test_charset_without_uid(self):
        self.client.use_uid = False
        self.client._imap.sort.return_value = ('OK', [''])

        self.client.sort('arrival', criteria=['\u261e', 'UNDELETED'], charset='utf-7')

        self.client._imap.sort.assert_called_once_with(
            '(ARRIVAL)',
            b'utf-7',
            b'(+Jh4-)', b'(UNDELETED)',
        )

    def test_unicode_with_uid(self):
        self.client._imap.uid.return_value = ('OK', [''])

        self.client.sort('arrival', criteria=['\u261e', 'UNDELETED'], charset='utf-7')

        self.client._imap.uid.assert_called_once_with(
            sort_command,
            '(ARRIVAL)',
            b'utf-7',
            b'(+Jh4-)', b'(UNDELETED)',
        )
