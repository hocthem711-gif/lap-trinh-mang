"""Kiểm tra JSON header và hàm nhận đủ byte cho giao thức mạng."""

import os
import socket
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from protocol import recv_exact, recv_message, send_message


class ProtocolTests(unittest.TestCase):
    """Tập hợp các ca kiểm thử đơn vị cho tầng giao thức (protocol layer)."""

    def test_message_round_trip(self):
        """Kiểm tra chu trình khép kín: Dict -> Gửi qua TCP socket -> Nhận & giải mã về Dict."""
        sender, receiver = socket.socketpair()
        try:
            expected = {"command": "GET", "name": "hello.txt"}
            send_message(sender, expected)
            self.assertEqual(recv_message(receiver), expected)
        finally:
            sender.close()
            receiver.close()

    def test_recv_exact_success(self):
        """Kiểm tra nhận đủ chính xác toàn bộ byte dữ liệu nhị phân."""
        sender, receiver = socket.socketpair()
        try:
            payload = b"Hello Socket TCP"
            sender.sendall(payload)
            self.assertEqual(recv_exact(receiver, len(payload)), payload)
        finally:
            sender.close()
            receiver.close()

    def test_recv_exact_detects_early_disconnect(self):
        """Kiểm tra khả năng phát hiện ngắt kết nối đột ngột (Premature EOF) khi chưa đủ byte."""
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
