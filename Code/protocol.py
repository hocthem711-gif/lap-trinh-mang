"""Quy ước gói tin: mỗi message là một dòng JSON UTF-8 kết thúc bằng '\n'."""

import json

CHUNK_SIZE = 4096
SOCKET_TIMEOUT = 30
MAX_HEADER_SIZE = 65536


def send_message(sock, message):
    """Mã hóa dict thành một dòng JSON và gửi đầy đủ."""
    data = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    # TCP là luồng byte; sendall đảm bảo gửi hết dữ liệu (send có thể gửi thiếu).
    sock.sendall(data)


def recv_message(sock):
    """Đọc header đến khi gặp newline, giới hạn kích thước header."""
    data = bytearray()
    while len(data) < MAX_HEADER_SIZE:
        # Đọc từng byte để không lấy lẫn byte đầu của nội dung file phía sau.
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