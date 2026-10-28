"""Quy ước gói tin và hàm gửi/nhận dữ liệu TCP dùng chung."""

import json
import socket

CHUNK_SIZE = 4096
SOCKET_TIMEOUT = 30
MAX_HEADER_SIZE = 65536


def send_message(sock: socket.socket, message: dict) -> None:
    """Mã hóa dict thành JSON UTF-8 một dòng và gửi đầy đủ."""
    data = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    # TCP là luồng byte; sendall đảm bảo toàn bộ header được đưa vào socket.
    sock.sendall(data)


def recv_message(sock: socket.socket) -> dict:
    """Đọc header đến newline, giới hạn kích thước để không nhận header vô hạn."""
    data = bytearray()
    while len(data) < MAX_HEADER_SIZE:
        # Đọc từng byte để không vô tình lấy lẫn byte đầu của nội dung file.
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
    """Nhận đủ size byte; báo lỗi nếu kết nối đóng giữa chừng."""
    if size < 0:
        raise ValueError("Kích thước cần nhận không được âm")

    data = bytearray()
    while len(data) < size:
        # recv có thể trả về ít byte hơn yêu cầu; lặp đến khi đủ N byte.
        chunk = sock.recv(min(CHUNK_SIZE, size - len(data)))
        if not chunk:
            raise ConnectionError(f"Kết nối đóng sớm ({len(data)}/{size} byte)")
        data.extend(chunk)
    return bytes(data)
