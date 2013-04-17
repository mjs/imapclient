from __future__ import unicode_literals

from imapclient import _imapclient_version_string
from imapclient.test.util import unittest

class TestVersionString(unittest.TestCase):

    def test_dot_oh(self):
        self.assertEqual(_imapclient_version_string((1, 0, 0, 'final')), '1.0')

    def test_minor(self):
        self.assertEqual(_imapclient_version_string((2, 1, 0, 'final')), '2.1')

    def test_point_release(self):
        self.assertEqual(_imapclient_version_string((1, 2, 3, 'final')), '1.2.3')

    def test_alpha(self):
        self.assertEqual(_imapclient_version_string((2, 1, 0, 'alpha')), '2.1-alpha')

    def test_beta_point(self):
        self.assertEqual(_imapclient_version_string((2, 1, 3, 'beta')), '2.1.3-beta')
