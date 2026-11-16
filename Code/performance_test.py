"""Đo thời gian và tốc độ tải một file ở hai mức đồng thời: 1 và 3."""

import argparse
import csv
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from client_core import download_file, list_files


def test_level(host, port, filename, jobs, workers):
    """Tải nhiều bản cùng lúc, đếm kết quả và tính tốc độ trung bình."""
    total_bytes = 0
    success = 0
    failures = 0

    with tempfile.TemporaryDirectory() as folder:
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            tasks = [
                pool.submit(download_file, host, port, filename, folder, lambda *_: None)
                for _ in range(jobs)
            ]
            for task in as_completed(tasks):
                try:
                    path, _ = task.result()
                    total_bytes += os.path.getsize(path)
                    success += 1
                except (OSError, RuntimeError, ValueError):
                    failures += 1
        seconds = time.perf_counter() - start

    speed = total_bytes / (1024 * 1024) / seconds if seconds else 0
    return success, failures, seconds, speed


def main():
    parser = argparse.ArgumentParser(description="Kiểm thử tải UDM_11")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--file", required=True, help="Tên file có trên Server")
    parser.add_argument("--jobs", type=int, default=6, help="Số lượt tải mỗi mức")
    args = parser.parse_args()

    if args.jobs < 3:
        parser.error("--jobs phải ít nhất là 3 để thử mức 3 lượt đồng thời")
    if args.file not in {item["name"] for item in list_files(args.host, args.port)}:
        parser.error("Không tìm thấy file trên Server")

    output = Path(__file__).resolve().parents[1] / "Extra"
    output.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = output / f"performance_{stamp}.csv"
    results = []

    for workers in (1, 3):
        success, failures, seconds, speed = test_level(
            args.host, args.port, args.file, args.jobs, workers
        )
        results.append({
            "workers": workers,
            "jobs": args.jobs,
            "success": success,
            "failures": failures,
            "seconds": seconds,
            "MiB_per_second": speed,
        })
        print(
            f"{workers} workers: {success}/{args.jobs} succeeded, "
            f"{failures} failed, {seconds:.2f} seconds, {speed:.2f} MiB/s"
        )

    columns = ["workers", "jobs", "success", "failures", "seconds", "MiB_per_second"]
    with result_file.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        for result in results:
            writer.writerow({
                **result,
                "seconds": f'{result["seconds"]:.3f}',
                "MiB_per_second": f'{result["MiB_per_second"]:.3f}',
            })

    print(f"CSV: {result_file}")


if __name__ == "__main__":
    main()
