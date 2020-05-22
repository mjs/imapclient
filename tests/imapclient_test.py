from imapclient.testable_imapclient import TestableIMAPClient as IMAPClient
from .util import unittest

from .util import unittest, patch, sentinel, Mock

class IMAPClientTest(unittest.TestCase):
    initial_state = 'NONAUTH'

    def setUp(self):
        self.client = IMAPClient()
        self.client.state = self.initial_state

        # mock standard low-level interfaces here
        self.patch_method('_command')
        self.patch_method('_get_response')
        self.patch_method('_simple_command')
        self.patch_method('_untagged_response')
        self.patch_method('_command_complete')

    def patch_method(self, name):
        """Patch a method in IMAPClient"""
        patcher = patch('imapclient.imapclient.IMAPClient.' + name)
        patcher.start().__func__ = Mock(__name__=name)
        self.addCleanup(patcher.stop)

