from imapclient.testable_imapclient import TestableIMAPClient as IMAPClient
import unittest


class IMAPClientTest(unittest.TestCase):
    def setUp(self):
        self.client = IMAPClient()
