"""Kiểm tra JSON header và hàm nhận đủ byte."""

import socket
import sys
import unittest
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from protocol import recv_message, send_message


class ProtocolTests(unittest.TestCase):
    def test_message_round_trip(self):
        sender, receiver = socket.socketpair()
        try:
            expected = {"command": "GET", "name": "hello.txt"}
            send_message(sender, expected)
            self.assertEqual(recv_message(receiver), expected)
        finally:
            sender.close()
            receiver.close()

if __name__ == "__main__":
    unittest.main()
