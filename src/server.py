"""Server TCP: lắng nghe Client và tạo một thread cho mỗi kết nối."""
import argparse
import logging
import socket
import threading

from file_service import handle_request
from protocol import SOCKET_TIMEOUT

def setup_logger() -> logging.Logger:
    """Ghi sự kiện Server ra console và file server.log."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler("server.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("udm11.server")

def handle_client(
    client: socket.socket,
    address: tuple[str, int],
    share_dir: str,
    logger: logging.Logger,
) -> None:
    """Phục vụ một Client rồi tự đóng socket."""
    logger.info("Client kết nối %s:%d", address[0], address[1])
    try:
        with client:
            client.settimeout(SOCKET_TIMEOUT)
            handle_request(client, share_dir, logger)
    except OSError:
        logger.exception("Lỗi kết nối với Client %s:%d", address[0], address[1])
    finally:
        logger.info("Client ngắt kết nối %s:%d", address[0], address[1])

def run_server(host: str, port: int, share_dir: str) -> None:
    """Bind/listen, nhận kết nối và dừng an toàn khi nhấn Ctrl+C."""
    logger = setup_logger()
    # Tạo TCP listener, cho phép chạy lại nhanh sau khi Server dừng.
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, port))
    listener.listen()
    # Timeout giúp vòng lặp thức dậy định kỳ để nhận Ctrl+C.
    listener.settimeout(1)
    logger.info("Server đang nghe tại %s:%d", host, port)

    try:
        while True:
            try:
                client, address = listener.accept()
            except socket.timeout:
                continue
            # Mỗi Client có thread riêng, nên Client chậm không chặn accept kế tiếp.
            worker = threading.Thread(
                target=handle_client,
                args=(client, address, share_dir, logger),
                daemon=True,
            )
            worker.start()
    except KeyboardInterrupt:
        logger.info("Nhận Ctrl+C, đang dừng Server")
    finally:
        # Luôn đóng listener để giải phóng port khi thoát vòng lặp.
        listener.close()
        logger.info("Server đã dừng")

def main() -> None:
    """Đọc tham số dòng lệnh và khởi chạy Server."""
    parser = argparse.ArgumentParser(description="UDM_11 Server")
    parser.add_argument("--host", required=True, help="IP/interface để lắng nghe")
    parser.add_argument("--port", type=int, required=True, help="Port TCP")
    parser.add_argument("--share-dir", required=True, help="Thư mục chia sẻ file")
    args = parser.parse_args()
    run_server(args.host, args.port, args.share_dir)

if __name__ == "__main__":
    main()
