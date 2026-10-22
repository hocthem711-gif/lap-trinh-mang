"""Quy ước gói tin đơn giản dùng chung giữa Client và Server."""

import json
import socket

CHUNK_SIZE = 4096


def send_message(sock: socket.socket, message: dict) -> None:
    """Gửi một object JSON thành một dòng kết thúc bằng newline."""
    data = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    sock.sendall(data)


def recv_message(sock: socket.socket) -> dict:
    """Đọc một dòng JSON từ TCP và đổi thành dict Python."""
    data = bytearray()
    while True:
        byte = sock.recv(1)
        if not byte:
            raise ConnectionError("Kết nối đóng trước khi nhận header")
        if byte == b"\n":
            break
        data.extend(byte)

    message = json.loads(data.decode("utf-8"))
    if not isinstance(message, dict):
        raise ValueError("Header phải là JSON object")
    return message
