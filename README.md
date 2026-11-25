# UDM_11 — Ứng dụng GUI tải nhiều file qua TCP/IP

**Mã đề tài:** UDM_11 — Download nhiều file  
**Mã nhóm:** NET_262701302_14  
**Môi trường:** Python 3.10 trở lên, Tkinter và thư viện chuẩn Python. Không cần cài package bên thứ ba.

Ứng dụng gồm Server cung cấp danh sách/nội dung file và Client GUI để tải file
qua TCP. Client hỗ trợ chọn/kéo nhiều file vào hàng đợi; mỗi file có trạng thái,
tốc độ và phần trăm tiến trình riêng. Mặc định tối đa 3 file được tải đồng thời.

## Thành viên và phân công

| Thành viên | Phần phụ trách |
|---|---|
| Trần Nguyễn Bảo Hoàng | `protocol.py`, `performance_test.py` |
| Nguyễn Thị Phương Hòa | `server.py` |
| Võ Trí Hoa | `file_service.py` |
| Nguyễn Khánh Đăng | `client_core.py` |
| Nguyễn Huỳnh Hoa | `client_gui.py` |

## Cấu trúc dự án

```text
Code/
├── protocol.py      # Định dạng và gửi/nhận header TCP
├── server.py        # TCP listener và thread phục vụ Client
├── file_service.py  # Xử lý LIST/GET, đọc và gửi file
├── client_core.py   # Kết nối Server, tải file và lưu xuống máy
├── client_gui.py    # Tkinter GUI, bảng trạng thái, hàng đợi và worker
├── performance_test.py
└── tests/           # Kiểm thử tự động
shared/              # File mẫu Server chia sẻ
downloads/           # Thư mục mặc định để Client lưu file tải xuống
Extra/               # CSV do benchmark tạo ra
```

## Yêu cầu và cách chạy

Chạy các lệnh từ thư mục gốc dự án. Trên máy Windows, mở hai cửa sổ PowerShell.

**Cửa sổ 1 — khởi động Server:**

```powershell
python Code\server.py --host 127.0.0.1 --port 5000 --share-dir "Code\shared"
```

**Cửa sổ 2 — khởi động Client GUI:**

```powershell
python Code\client_gui.py --host 127.0.0.1 --port 5000 --download-dir ".\downloads" --max-downloads 3
```

Server và Client là hai tiến trình riêng, kể cả khi chạy trên cùng máy.
Để kết nối từ máy khác, thay `127.0.0.1` bằng IP LAN của máy Server và cho phép
cổng TCP đã chọn qua tường lửa. Thư mục `--share-dir` phải tồn tại.

## Giao thức trao đổi

Mỗi header là một object JSON UTF-8 trên một dòng, kết thúc bằng ký tự xuống
dòng (`\n`). `LIST` và `GET` dùng kết nối TCP riêng. Sau header thành công của
`GET`, nội dung file được gửi dưới dạng byte nhị phân, không phải JSON.

Ví dụ yêu cầu tải file:

```json
{"command":"GET","name":"a.txt"}
```

Phản hồi thành công `GET` thông báo kích thước trước khi gửi nội dung:

```json
{"status":"OK","size":12}
```

Sau header trên, Server gửi đúng 12 byte nội dung file. Phản hồi lỗi có dạng:

```json
{"status":"ERROR","code":"FILE_NOT_FOUND","message":"Không tìm thấy file trong thư mục chia sẻ"}
```

`LIST` trả danh sách tên và kích thước, ví dụ:

```json
{"status":"OK","files":[{"name":"a.txt","size":12}]}
```

## Cách hoạt động

Mô hình: `Client GUI → Client Core → TCP socket → Server → File Service`.

1. Client gửi `LIST`; Server trả danh sách file trong thư mục chia sẻ.
2. Khi người dùng chọn/kéo file, GUI tạo một job tải và đưa vào hàng đợi.
3. Các worker xử lý tối đa số job được cấu hình; mỗi file dùng kết nối riêng.
4. Server gửi header có kích thước, rồi truyền nội dung file theo các khối 4096 byte.
5. Client ghi vào file `.part`; chỉ sau khi nhận đủ byte mới đổi sang tên hoàn chỉnh.
6. Nếu tên đích đã tồn tại, Client chọn tên như `a (1).txt` để không ghi đè file cũ.
7. Lỗi của một job được báo riêng và không dừng các job còn lại.

## Kiểm thử

Chạy toàn bộ kiểm thử tự động từ thư mục gốc:

```powershell
python -m unittest discover -s Code\tests -v
```

Các test dùng dữ liệu tạm cho những ca LIST/GET, metadata sai, file không tồn
tại, tên file không hợp lệ, file trùng tên, tải bị ngắt và logic hàng đợi/kéo-thả.
`test_gui_logic.py` kiểm tra logic bằng widget giả; cần chạy Client GUI riêng để
nghiệm thu giao diện trực quan. Máy Python cần có Tkinter.

### Kiểm tra thủ công trước khi nộp

- Làm mới danh sách Server, rồi tải một file và kiểm tra nội dung file nhận được.
- Kéo nhiều file vào khu vực tải; xác nhận số job đang chạy không vượt quá
  `--max-downloads` và các job khác chờ trong hàng đợi.
- Tải file rỗng, file có dấu cách/tên tiếng Việt và cùng một file hai lần.
- Bắt đầu tải `demo-large.bin`, dừng Server bằng `Ctrl+C`; Client cần báo lỗi,
  các file `.part` dở dang cần được dọn.
- Kiểm tra `server.log` để xem log kết nối và lỗi phía Server.

### File mẫu trong `shared/`

| File | Dùng để kiểm tra |
|---|---|
| `test-empty.bin` | Tải file 0 byte |
| `test file name co space.txt` | Tên file có dấu cách |
| `test-tieng-viet.txt` | Nội dung UTF-8 tiếng Việt |
| `test-medium-1mb.bin` | Tải file nhị phân 1 MiB |
| `demo-test-10mb.bin` | Tải/benchmark file nhị phân 10 MiB |
| `demo-large.bin` | Tải file lớn 50 MiB và thử ngắt kết nối |

## Benchmark

Khởi động Server trước. Từ terminal khác, chạy lệnh sau:

```powershell
python Code\performance_test.py --host 127.0.0.1 --port 5000 --file demo-larger.bin --jobs 6
```

Script chạy hai mức đồng thời: 1 và 3 worker. `--jobs` là tổng số lượt tải
ở mỗi mức (mặc định 6). Kết quả thành công/thất bại, thời gian và throughput
được lưu thành CSV trong `Extra\`. Đây là benchmark trên kết nối được chỉ định;
kết quả localhost không đại diện cho tốc độ trên mạng LAN/Internet.

Khi đưa kết quả vào báo cáo, ghi rõ CPU, RAM, hệ điều hành, kích thước file,
số job, địa chỉ chạy benchmark (localhost hay LAN) và số liệu CSV thực tế.
Không dùng số liệu mẫu hoặc số đo trên máy khác làm kết quả của nhóm.

## Giới hạn

- Chưa hỗ trợ Pause/Resume, đăng nhập hoặc mã hóa TLS; các chức năng này ngoài phạm vi.
- Tiến trình tải hiển thị bằng phần trăm trong bảng trạng thái, không phải thanh progress bar đồ họa.

## Video demo

**Link video Public/Unlisted:** nhóm cập nhật link sau khi tải video lên.
