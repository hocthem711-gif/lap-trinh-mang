"""Server TCP: nhận yêu cầu LIST/GET và gửi file trong thư mục chia sẻ."""

import argparse
import logging
import os
import socket
import threading

from file_service import handle_request
from protocol import SOCKET_TIMEOUT


def handle_client(client, address, share_dir, logger):
    """Phục vụ một Client rồi tự đóng socket; lỗi của Client này không ảnh hưởng Client khác."""
    logger.info("Client kết nối %s:%d", address[0], address[1])
    try:
        with client:
            client.settimeout(SOCKET_TIMEOUT)
            handle_request(client, share_dir, logger)
    except OSError as error:  # gồm ConnectionError và socket.timeout
        logger.warning("Lỗi với Client %s:%d: %s", address[0], address[1], error)
    finally:
        logger.info("Client ngắt kết nối %s:%d", address[0], address[1])


def run_server(host, port, share_dir):
    """Bind/listen, nhận kết nối và dừng an toàn khi nhấn Ctrl+C."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler("server.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    logger = logging.getLogger("udm11.server")

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Cho phép chạy lại Server ngay sau khi dừng mà không bị lỗi "port đang dùng".
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((host, port))
        listener.listen()
        # Timeout để vòng lặp thức dậy định kỳ, kịp nhận Ctrl+C.
        listener.settimeout(1)
        logger.info("Server đang nghe tại %s:%d, thư mục chia sẻ: %s", host, port, share_dir)

        while True:
            try:
                client, address = listener.accept()
            except socket.timeout:
                continue
            # Mỗi Client một thread để Client chậm không chặn accept kế tiếp.
            threading.Thread(
                target=handle_client,
                args=(client, address, share_dir, logger),
                daemon=True,
            ).start()
    except KeyboardInterrupt:
        logger.info("Nhận Ctrl+C, đang dừng Server")
    finally:
        listener.close()  # luôn giải phóng port
        logger.info("Server đã dừng")


def main():
    parser = argparse.ArgumentParser(description="UDM_11 Server")
    parser.add_argument("--host", required=True, help="IP/interface để lắng nghe")
    parser.add_argument("--port", type=int, required=True, help="Cổng TCP")
    parser.add_argument("--share-dir", required=True, help="Thư mục chứa file chia sẻ")
    args = parser.parse_args()
    if not os.path.isdir(args.share_dir):
        parser.error("--share-dir không phải thư mục tồn tại")
    run_server(args.host, args.port, args.share_dir)


if __name__ == "__main__":
    main()
