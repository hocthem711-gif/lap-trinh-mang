"""Server TCP checkpoint 1: chờ Client và gửi file được yêu cầu."""

import argparse  
import logging  
import socket  
from file_service import handle_client 
from logger_setup import create_logger  


def parse_args() -> argparse.Namespace: 
    """Đọc IP, port và thư mục chia sẻ từ lệnh chạy."""
    parser = argparse.ArgumentParser(description="UDM_11 demo checkpoint 1")  
    parser.add_argument("--host", default="127.0.0.1") 
    parser.add_argument("--port", type=int, default=5000) 
    parser.add_argument("--share-dir", required=True) 
    return parser.parse_args()  

def run_server(host: str, port: int, share_dir: str) -> None: 
    """Lắng nghe kết nối TCP và xử lý lần lượt từng Client."""
    logger = create_logger("demo.server") 
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
    server_socket.bind((host, port))
    server_socket.listen() 
    server_socket.settimeout(1.0)  
    logger.info("Server đang nghe tại %s:%d", host, port) 

    try: 
        while True:  
            try:  
                client_socket, address = server_socket.accept() 
            except socket.timeout:  
                continue  
            logger.info("Client kết nối: %s:%d", address[0], address[1])  
            with client_socket:  
                client_socket.settimeout(10)  
                handle_client(client_socket, share_dir, logger) 
    except KeyboardInterrupt:  
        logger.info("Người dùng yêu cầu dừng Server") 
    finally: 
        server_socket.close() 
        logger.info("Server đã dừng") 


def main() -> None:  
    """Khởi động Server với cấu hình trên terminal."""
    args = parse_args() 
    run_server(args.host, args.port, args.share_dir)  


if __name__ == "__main__":  
    main() 
