from .testable_imapclient import TestableIMAPClient as IMAPClient
from .util import unittest


class IMAPClientTest(unittest.TestCase):

    def setUp(self):
        self.client = IMAPClient()
