"""Quy ước gói tin đơn giản dùng chung giữa Client và Server."""

import json  # Chuyển dữ liệu Python thành JSON và ngược lại.
import socket  # Dùng kiểu socket trong chú thích kiểu (type hints).

CHUNK_SIZE = 4096  # Số byte tối đa mỗi lần đọc file để truyền qua mạng.


def send_message(sock: socket.socket, message: dict) -> None:  # Gửi một header điều khiển JSON.
    """Gửi một object JSON thành một dòng kết thúc bằng newline."""
    data = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")  # Serialize dict, thêm dấu kết thúc dòng và mã hóa UTF-8.
    sock.sendall(data)  # Gửi đủ header; sendall tiếp tục gửi nếu lần gửi đầu chưa đủ.


def recv_message(sock: socket.socket) -> dict:  # Nhận một header điều khiển từ socket.
    """Đọc một dòng JSON từ TCP và đổi thành dict Python."""
    data = bytearray()  # Bộ đệm để ghép các byte header nhận được.
    while True:  # Tiếp tục nhận tới khi thấy newline kết thúc header.
        byte = sock.recv(1)  # Đọc một byte để không đọc lấn sang body nhị phân.
        if not byte:  # Byte rỗng nghĩa là đầu bên kia đã đóng kết nối.
            raise ConnectionError("Kết nối đóng trước khi nhận header")  # Không có header đầy đủ nên báo lỗi.
        if byte == b"\n":  # Protocol quy định newline là dấu kết thúc header.
            break  # Dừng vòng lặp; những byte sau thuộc phần tiếp theo.
        data.extend(byte)  # Thêm byte vừa nhận vào vùng chứa header.

    message = json.loads(data.decode("utf-8"))  # Giải mã UTF-8 rồi parse chuỗi JSON.
    if not isinstance(message, dict):  # Các lệnh của protocol phải là object/dict.
        raise ValueError("Header phải là JSON object")  # Từ chối JSON dạng list, số hay chuỗi.
    return message  # Trả object để module gọi xử lý command/status.
