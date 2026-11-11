"""Kiểm tra JSON header và hàm nhận đủ byte cho giao thức mạng."""

import os
import socket
import sys
import unittest

# Đưa thư mục 'src' vào sys.path để import module protocol từ bất kỳ đâu
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from protocol import recv_exact, recv_message, send_message


class ProtocolTests(unittest.TestCase):
    """Tập hợp các ca kiểm thử đơn vị cho tầng giao thức (protocol layer)."""

    def test_message_round_trip(self):
        """Kiểm tra chu trình khép kín: Dict -> Gửi qua TCP socket -> Nhận & giải mã về Dict."""
        # Tạo cặp socket kết nối trực tiếp trong bộ nhớ (không cần mở cổng mạng thật)
        sender, receiver = socket.socketpair()
        try:
            expected = {"command": "GET", "name": "hello.txt"}
            # Gửi thông điệp JSON có kết thúc bằng '\n'
            send_message(sender, expected)
            # Nhận và phân tách gói tin, so khớp tính toàn vẹn 100% của dữ liệu
            self.assertEqual(recv_message(receiver), expected)
        finally:
            # Luôn đóng cả hai socket trong khối finally để tránh rò rỉ tài nguyên mạng của HĐH
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
            # Phía gửi chỉ truyền 5 byte rồi đóng kết nối đột ngột
            sender.sendall(b"short")
            sender.close()

            # Phía nhận mong đợi 10 byte; hàm recv_exact phải bắt được lỗi và ném ConnectionError
            with self.assertRaises(ConnectionError):
                recv_exact(receiver, 10)
        finally:
            receiver.close()


if __name__ == "__main__":
    unittest.main()

