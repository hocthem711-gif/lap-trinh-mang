"""Quy ước gói tin và hàm gửi/nhận dữ liệu TCP dùng chung."""

import json
import socket

CHUNK_SIZE = 4096        # Kích thước khối đệm đọc/ghi (4 KB)
SOCKET_TIMEOUT = 30      # Timeout tránh treo socket vô hạn (giây)
MAX_HEADER_SIZE = 65536  # Giới hạn header tối đa chống DoS/tràn RAM (64 KB)


def send_message(sock: socket.socket, message: dict) -> None:
    """Mã hóa dict thành JSON UTF-8 kết thúc bằng '\\n' và gửi đầy đủ."""
    # Thêm '\n' làm ranh giới gói tin (framing), hỗ trợ tiếng Việt
    data = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    # sendall đảm bảo truyền trọn vẹn toàn bộ byte trong luồng TCP
    sock.sendall(data)


def recv_message(sock: socket.socket) -> dict:
    """Đọc header đến newline '\\n', ném lỗi nếu quá giới hạn kích thước."""
    data = bytearray()
    while len(data) < MAX_HEADER_SIZE:
        # Đọc từng byte để dừng đúng ranh giới '\n', tránh lẹm vào dữ liệu file
        byte = sock.recv(1)
        if not byte:
            raise ConnectionError("Kết nối đóng trước khi nhận đủ header")
        if byte == b"\n":
            message = json.loads(data.decode("utf-8"))
            if not isinstance(message, dict):
                raise ValueError("Header phải là JSON object")
            return message
        data.extend(byte)

    raise ValueError("Header vượt quá kích thước cho phép")


def recv_exact(sock: socket.socket, size: int) -> bytes:
    """Nhận đủ chính xác size byte; báo lỗi nếu kết nối ngắt giữa chừng."""
    if size < 0:
        raise ValueError("Kích thước cần nhận không được âm")

    data = bytearray()
    while len(data) < size:
        # Lặp gom từng chunk cho đến khi đủ số byte yêu cầu
        chunk = sock.recv(min(CHUNK_SIZE, size - len(data)))
        if not chunk:
            raise ConnectionError(f"Kết nối đóng sớm ({len(data)}/{size} byte)")
        data.extend(chunk)

    return bytes(data)
