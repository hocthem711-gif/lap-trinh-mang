# UDM_11 - Ứng dụng tải nhiều file qua TCP

Đồ án môn **Lập trình mạng**: ứng dụng Client có giao diện Tkinter để xem danh sách file trên Server và tải một hoặc nhiều file qua TCP. Server và Client là hai chương trình riêng biệt; mỗi lệnh `LIST` và mỗi lần tải `GET` sử dụng một kết nối TCP riêng.

## Thành viên và phân công

| STT | Thành viên | MSSV | Module phụ trách |
|---:|---|---:|---|
| 1 | Trần Nguyễn Bảo Hoàng | 066206004994 | `Code/protocol.py` - giao thức và đóng gói dữ liệu |
| 2 | Nguyễn Thị Phương Hòa | 058306000195 | `Code/server.py` - TCP listener và quản lý kết nối |
| 3 | Võ Trí Hoa | 082306004425 | `Code/file_service.py` - xử lý `LIST`, `GET` và truyền file |
| 4 | Nguyễn Khánh Đăng | 080206013032 | `Code/client_core.py` - kết nối Client, nhận và lưu file |
| 5 | Nguyễn Huỳnh Hoa | 083306013301 | `Code/client_gui.py` - giao diện, kéo thả và hàng đợi |

## Cấu trúc project

```text
lap-trinh-mang/
├── Code/
│   ├── Shared/                 # File mẫu để Server chia sẻ
│   ├── tests/                  # Kiểm thử giao thức và truyền file
│   ├── client_core.py
│   ├── client_gui.py
│   ├── file_service.py
│   ├── protocol.py
│   └── server.py
├── DOCX/                       # Báo cáo và tài liệu Word
├── Extra/                      # Tài liệu, dữ liệu bổ sung
├── PPTX/                       # Slide thuyết trình
├── .gitignore
└── README.md
```

Thư mục `Downloads/` được tạo khi tải file nếu chưa tồn tại và đã được Git bỏ qua. File log (`*.log`), file tạm (`*.part`) và cache Python cũng không được đưa lên Git.

## Yêu cầu

- Python 3.10 trở lên.
- Chỉ dùng thư viện chuẩn Python: socket, threading, queue, json, os, argparse, logging, time, tempfile và Tkinter/ttk.
- Máy cần có Tkinter để chạy giao diện đồ họa.
- Không cần cài package Python bên ngoài.

## Chạy ứng dụng

Mở hai cửa sổ Terminal tại thư mục gốc project.

### 1. Khởi động Server

Ví dụ trên cùng một máy:

```powershell
python Code/server.py --host 127.0.0.1 --port 5000 --share-dir Code/Shared
```

Để Client ở máy khác trong mạng LAN kết nối được, bind Server vào interface mạng, ví dụ:

```powershell
python Code/server.py --host 0.0.0.0 --port 5000 --share-dir Code/Shared
```

Trong trường hợp này, Client phải dùng địa chỉ IP LAN của máy chạy Server; firewall cũng cần cho phép kết nối TCP đến port đã chọn. Server ghi log ra console và `server.log`. Nhấn `Ctrl+C` để dừng.

### 2. Khởi động Client

```powershell
python Code/client_gui.py --host 127.0.0.1 --port 5000 --download-dir Downloads --max-downloads 3
```

Thay `127.0.0.1` bằng IP/hostname của Server nếu Client chạy trên máy khác. Tham số `--max-downloads` phải là số nguyên dương và giới hạn số lượt tải đồng thời trong **một cửa sổ Client**.

### 3. Sử dụng giao diện

1. Nút **Refresh** lấy lại danh sách file Server.
2. Chọn một hoặc nhiều file trong danh sách bên trái (Ctrl/Shift để chọn nhiều).
3. Kéo lựa chọn sang khu vực Download bên phải, hoặc nhấn **Thêm file đã chọn**.
4. Mỗi file có hàng riêng với trạng thái, tốc độ và phần trăm tiến trình. Những file vượt giới hạn tải đồng thời sẽ ở trạng thái chờ.
5. Khi tên file đã tồn tại trong thư mục đích, Client không ghi đè mà chọn tên tiếp theo, ví dụ `hello (1).txt`.

Các trạng thái gồm chờ, đang tải, hoàn thành, lỗi và đã tồn tại/đổi tên. Lỗi ở một lượt tải được báo trên hàng tương ứng, không dừng những lượt tải khác.

## Giao thức TCP

TCP là luồng byte nên mỗi header JSON được mã hóa UTF-8 và kết thúc bằng byte xuống dòng `\n`. Với `GET`, header phản hồi được gửi trước, sau đó Server gửi đúng số byte nội dung file; phần thân nhị phân không có dấu phân cách JSON.

### `LIST`

Client kết nối, gửi:

```json
{"command":"LIST"}
```

Server phản hồi một dòng JSON:

```json
{"status":"OK","files":[{"name":"hello.txt","size":20}]}
```

`size` tính bằng byte. Nếu không đọc được thư mục chia sẻ, Server trả `status: ERROR` với mã lỗi và thông báo.

### `GET`

Client mở một kết nối mới cho file cần tải và gửi:

```json
{"command":"GET","name":"hello.txt"}
```

Nếu thành công, Server gửi header:

```json
{"status":"OK","size":20}
```

Ngay sau newline của header, Server gửi nội dung file theo các khối tối đa `CHUNK_SIZE` (4096 byte). Client đọc cho đến khi đủ `size` byte. Nếu có lỗi, Server trả header JSON `status: ERROR`, kèm `code` và `message`; ví dụ `INVALID_NAME`, `FILE_NOT_FOUND`, `BAD_REQUEST` hoặc `INTERNAL_ERROR`.

### Trình tự và xử lý file chưa hoàn chỉnh

1. Client mở TCP socket có timeout và gửi một header JSON.
2. Server nhận header, xử lý lệnh, rồi gửi header phản hồi.
3. Với `GET` thành công, Server gửi body nhị phân; Client nhận và ghi vào file tạm `.part`.
4. Chỉ khi nhận đủ kích thước đã khai báo, Client mới đổi file tạm thành tên đích. Khi kết nối bị ngắt hoặc ghi file lỗi, file `.part` được dọn và lượt tải đó báo lỗi.
5. Hai phía đóng socket sau khi hoàn tất hoặc gặp lỗi.

Server chỉ phục vụ file nằm trực tiếp trong thư mục chia sẻ và từ chối tên chứa đường dẫn hoặc `..`. Client không ghi đè file đã có. Mỗi lần tải dùng kết nối riêng; Server phục vụ các kết nối bằng thread riêng.

## Kiểm thử

Chạy từ thư mục gốc project:

```powershell
python -m unittest discover -s Code/tests -v
```

Bộ test kiểm tra đóng gói header, phát hiện ngắt kết nối khi nhận thiếu byte, từ chối path traversal, phản hồi file không tồn tại, truyền file qua TCP, dọn file `.part` khi truyền bị ngắt và tự đổi tên khi đích đã tồn tại.

## Ghi chú phạm vi

- Ứng dụng không hỗ trợ pause/resume.
- Giới hạn đồng thời được áp dụng ở Client; đây không phải giới hạn tổng toàn Server.
- Giao thức hiện không mã hóa dữ liệu và không có xác thực người dùng; chỉ chia sẻ với các máy tin cậy trong mạng phù hợp.
