"""Kiểm tra JSON header và hàm nhận đủ byte."""

import os
import socket
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from protocol import recv_exact, recv_message, send_message


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

    def test_recv_exact_detects_early_disconnect(self):
        sender, receiver = socket.socketpair()
        try:
            sender.sendall(b"short")
            sender.close()
            with self.assertRaises(ConnectionError):
                recv_exact(receiver, 10)
        finally:
            receiver.close()


if __name__ == "__main__":
    unittest.main()
