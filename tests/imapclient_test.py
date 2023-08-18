import unittest

from imapclient.testable_imapclient import TestableIMAPClient as IMAPClient


class IMAPClientTest(unittest.TestCase):
    def setUp(self):
        self.client = IMAPClient()
